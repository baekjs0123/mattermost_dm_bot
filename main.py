import os
import re
import json
import requests
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# .env 파일을 읽어옵니다.
load_dotenv()

app = FastAPI()

# 여러 Slash Command Token을 콤마로 구분해서 읽어옵니다.
# 예: SLASH_COMMAND_TOKENS=토큰1,토큰2,토큰3
SLASH_COMMAND_TOKENS = {
    item.strip()
    for item in os.getenv("SLASH_COMMAND_TOKENS", "").split(",")
    if item.strip()
}

# Webhook URL을 저장할 JSON 파일입니다.
REGISTRY_FILE = Path("webhook_registry.json")

# 여러 요청이 동시에 등록/삭제할 때 파일이 꼬이지 않도록 Lock을 사용합니다.
# threading.Lock은 한 스레드가 Lock을 잡고 있는 동안 다른 스레드가 기다리게 해줍니다.
registry_lock = threading.Lock()


@app.get("/")
def health_check():
    """
    서버 상태 확인용 API입니다.
    Oracle VM 배포 후 브라우저에서 접속해서 서버가 살아있는지 확인할 수 있습니다.
    """
    return {
        "status": "ok",
        "service": "mattermost-dm-broadcast"
    }


def load_registry() -> dict:
    """
    webhook_registry.json 파일을 읽어옵니다.

    파일이 아직 없으면 기본 구조를 반환합니다.
    """
    if not REGISTRY_FILE.exists():
        return {"users": {}}

    with REGISTRY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_registry(data: dict):
    """
    webhook_registry.json 파일을 저장합니다.

    바로 원본 파일에 덮어쓰지 않고,
    임시 파일에 먼저 쓴 뒤 os.replace 방식으로 교체합니다.

    이렇게 하면 저장 중 문제가 생겨도 원본 파일이 깨질 가능성을 줄일 수 있습니다.
    """
    temp_file = REGISTRY_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    os.replace(temp_file, REGISTRY_FILE)


def is_valid_mattermost_webhook_url(webhook_url: str) -> bool:
    """
    사용자가 등록한 URL이 Mattermost Webhook URL 형태인지 최소 검증합니다.

    보안상 아무 URL이나 등록되면 안 됩니다.
    최소한 meeting.ssafy.com의 /hooks/ 경로인지 확인합니다.
    """
    try:
        parsed = urlparse(webhook_url)

        if parsed.scheme != "https":
            return False

        if parsed.netloc != "meeting.ssafy.com":
            return False

        if not parsed.path.startswith("/hooks/"):
            return False

        return True

    except Exception:
        return False


def get_registered_webhook_url(username: str):
    """
    등록 파일에서 특정 사용자의 Webhook URL을 조회합니다.
    """
    with registry_lock:
        registry = load_registry()

    user_info = registry.get("users", {}).get(username)

    if not user_info:
        return None

    return user_info.get("webhook_url")


def register_webhook_url(username: str, webhook_url: str):
    """
    실행자 username 기준으로 Webhook URL을 등록합니다.
    """
    with registry_lock:
        registry = load_registry()

        registry.setdefault("users", {})
        registry["users"][username] = {
            "webhook_url": webhook_url,
            "registered_at": datetime.now().isoformat(timespec="seconds")
        }

        save_registry(registry)


def delete_webhook_url(username: str) -> bool:
    """
    실행자 username 기준으로 Webhook URL 등록을 삭제합니다.

    삭제한 값이 있으면 True,
    원래 등록된 값이 없으면 False를 반환합니다.
    """
    with registry_lock:
        registry = load_registry()
        users = registry.setdefault("users", {})

        if username not in users:
            return False

        del users[username]
        save_registry(registry)

    return True


def mask_webhook_url(webhook_url: str) -> str:
    """
    응답에 Webhook URL 전체를 노출하지 않기 위해 일부만 보여줍니다.
    """
    if len(webhook_url) <= 20:
        return "등록됨"

    return webhook_url[:34] + "..." + webhook_url[-6:]


def send_webhook_dm(webhook_url: str, target_username: str, message: str):
    """
    특정 발송자의 Incoming Webhook URL을 사용해서
    대상 사용자에게 DM을 보냅니다.

    channel 값에 @username을 넣으면 해당 사용자에게 DM이 발송됩니다.
    """
    payload = {
        "channel": f"@{target_username}",
        "text": message,
    }

    response = requests.post(
        webhook_url,
        json=payload,
        timeout=10,
    )

    if response.status_code == 200 and response.text.strip() == "ok":
        return True, None

    return False, f"{response.status_code} / {response.text}"


@app.post("/mattermost/dm-broadcast")
async def dm_broadcast(
    text: str = Form(""),
    user_name: str = Form(""),
    token: str = Form(""),
):
    """
    Mattermost Slash Command 요청 처리 API입니다.

    사용 예:
    /dm 등록 https://meeting.ssafy.com/hooks/...
    /dm 등록확인
    /dm 등록삭제
    /dm @user1 @user2 오늘 14시 회의입니다.
    """

    # SLASH_COMMAND_TOKENS가 비어 있으면 토큰 검증을 하지 않습니다.
    # 값이 하나라도 있으면, 요청으로 들어온 token이 목록 안에 있어야 합니다.
    if SLASH_COMMAND_TOKENS and token not in SLASH_COMMAND_TOKENS:
        return JSONResponse({
        "response_type": "ephemeral",
        "text": "잘못된 요청입니다. 등록되지 않은 Slash Command token입니다."
        })

    # 입력값 앞뒤 공백 제거
    text = text.strip()

    # 2. 등록 명령어 처리
    # 예: /dm 등록 https://meeting.ssafy.com/hooks/xxxx
    if text.startswith("등록 "):
        webhook_url = text.replace("등록 ", "", 1).strip()

        if not is_valid_mattermost_webhook_url(webhook_url):
            return JSONResponse({
                "response_type": "ephemeral",
                "text": (
                    "Webhook URL 형식이 올바르지 않습니다.\n\n"
                    "예: `/dm 등록 https://meeting.ssafy.com/hooks/xxxx`"
                )
            })

        register_webhook_url(user_name, webhook_url)

        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                f"@{user_name}님의 Webhook URL 등록이 완료되었습니다.\n"
                "이제 `/dm @대상자 메시지` 형식으로 사용할 수 있습니다."
            )
        })

    # 3. 등록 확인 명령어 처리
    # 예: /dm 등록확인
    if text == "등록확인":
        webhook_url = get_registered_webhook_url(user_name)

        if not webhook_url:
            return JSONResponse({
                "response_type": "ephemeral",
                "text": (
                    f"@{user_name}님의 Webhook URL이 아직 등록되어 있지 않습니다.\n\n"
                    "먼저 아래 형식으로 등록하세요.\n"
                    "`/dm 등록 https://meeting.ssafy.com/hooks/xxxx`"
                )
            })

        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                f"@{user_name}님의 Webhook URL이 등록되어 있습니다.\n"
                f"등록값: `{mask_webhook_url(webhook_url)}`"
            )
        })

    # 4. 등록 삭제 명령어 처리
    # 예: /dm 등록삭제
    if text == "등록삭제":
        deleted = delete_webhook_url(user_name)

        if not deleted:
            return JSONResponse({
                "response_type": "ephemeral",
                "text": f"@{user_name}님에게 삭제할 Webhook URL 등록값이 없습니다."
            })

        return JSONResponse({
            "response_type": "ephemeral",
            "text": f"@{user_name}님의 Webhook URL 등록을 삭제했습니다."
        })

    # 5. 도움말
    if text in ("", "도움말", "help"):
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                "DM 명령어 사용법입니다.\n\n"
                "1. Incoming Webhook 만들기\n"
                "Mattermost 왼쪽 위 팀 이름 또는 메뉴 버튼을 누릅니다.\n"
                "`Integrations` 또는 `통합` 메뉴로 이동합니다.\n"
                "`Incoming Webhooks`를 선택합니다.\n"
                "`Add Incoming Webhook` 또는 `Incoming Webhook 추가`를 누릅니다.\n"
                "이름에는 `DM 공지 - 본인이름`처럼 알아보기 쉬운 값을 입력합니다.\n"
                "기본 채널은 본인이 접근 가능한 채널을 선택합니다.`(1.공지사항 추천)` 실제 DM 발송 대상은 명령어의 `@username`으로 지정됩니다.\n"
                "저장한 뒤 생성된 `https://meeting.ssafy.com/hooks/...` 주소를 복사합니다.\n"
                "Webhook URL은 비밀번호처럼 관리하고 공개 채널이나 문서에 노출하지 마세요.\n\n"
                "2. Webhook 등록\n"
                "`/dm 등록 https://meeting.ssafy.com/hooks/xxxx`\n\n"
                "3. 등록 확인\n"
                "`/dm 등록확인`\n\n"
                "4. 등록 삭제\n"
                "`/dm 등록삭제`\n\n"
                "5. DM 발송\n"
                "`/dm @user1 @user2 오늘 14시 회의입니다.`"
            )
        })

    # 6. DM 발송 전, 실행자의 Webhook URL 조회
    webhook_url = get_registered_webhook_url(user_name)

    if not webhook_url:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                f"@{user_name}님의 Webhook URL이 등록되어 있지 않습니다.\n\n"
                "먼저 본인 계정으로 Incoming Webhook을 만든 뒤 아래처럼 등록하세요.\n"
                "`/dm 등록 https://meeting.ssafy.com/hooks/xxxx`"
            )
        })

    # 7. @username 목록 추출
    usernames = re.findall(r"@([a-zA-Z0-9._-]+)", text)

    if not usernames:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                "대상자를 찾지 못했습니다.\n"
                "예: `/dm @user1 @user2 오늘 14시 회의입니다.`"
            )
        })

    # 8. 메시지 본문 추출
    message = re.sub(r"@([a-zA-Z0-9._-]+)", "", text).strip()

    if not message:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": (
                "보낼 메시지가 없습니다.\n"
                "예: `/dm @user1 @user2 오늘 14시 회의입니다.`"
            )
        })

    # 9. 중복 대상자 제거
    usernames = list(dict.fromkeys(usernames))

    success_users = []
    failed_users = []

    # 10. 사용자별 DM 발송
    for target_username in usernames:
        ok, error = send_webhook_dm(
            webhook_url=webhook_url,
            target_username=target_username,
            message=message,
        )

        if ok:
            success_users.append(f"@{target_username}")
        else:
            failed_users.append(f"@{target_username}: {error}")

    # 11. 명령 실행자에게만 결과 표시
    result_text = (
        f"DM 발송 처리 완료\n\n"
        f"발송자: @{user_name}\n"
        f"성공: {len(success_users)}명\n"
        f"실패: {len(failed_users)}명"
    )

    if success_users:
        result_text += "\n\n성공 대상:\n" + ", ".join(success_users)

    if failed_users:
        result_text += "\n\n실패 대상:\n" + "\n".join(failed_users)

    return JSONResponse({
        "response_type": "ephemeral",
        "text": result_text
    })
