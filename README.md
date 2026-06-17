# Mattermost 개인별 DM 공지 봇 사용 설명서

이 프로젝트는 Mattermost의 Slash Command를 이용해 여러 사용자에게 같은 내용의 DM을 보내는 FastAPI 서버입니다.

각 사용자는 본인의 Incoming Webhook URL을 직접 등록한 뒤 DM 공지 기능을 사용할 수 있습니다. 운영자가 사용자별 URL을 `.env`에 추가하거나 서버를 재시작할 필요가 없습니다.

---

## 1. 주요 기능

- 사용자 본인의 Incoming Webhook URL 등록
- 등록된 Webhook URL 확인
- 등록된 Webhook URL 삭제
- 여러 Mattermost 사용자에게 같은 내용의 DM 발송
- 중복 대상자 자동 제거
- 발송 성공 및 실패 결과 표시
- Slash Command Token 검증
- Webhook URL 형식 검증

Mattermost에서 사용하는 명령어는 다음과 같습니다.

```text
/dm 등록 https://meeting.ssafy.com/hooks/본인의웹훅주소
/dm 등록확인
/dm 등록삭제
/dm @user1 @user2 보낼 메시지
/dm 도움말
```

---

## 2. 동작 원리

DM 공지를 보내는 전체 과정은 다음과 같습니다.

1. 사용자가 Mattermost에서 `/dm` 명령어를 입력합니다.
2. Mattermost가 FastAPI 서버의 `/mattermost/dm-broadcast` 주소로 요청을 보냅니다.
3. 서버가 요청의 Slash Command Token을 확인합니다.
4. 서버가 명령어를 실행한 사용자의 Mattermost username을 확인합니다.
5. 서버가 `webhook_registry.json`에서 해당 사용자의 Webhook URL을 찾습니다.
6. 입력 내용에서 `@username` 형식의 DM 대상자를 추출합니다.
7. 각 대상자에게 등록된 Webhook URL을 사용해 DM을 보냅니다.
8. 성공 및 실패 결과를 명령어 실행자에게만 보여줍니다.

결과 메시지는 `ephemeral` 방식이므로 명령어를 실행한 본인에게만 표시됩니다.

### Webhook URL 등록 과정

사용자가 아래 명령어를 입력하면:

```text
/dm 등록 https://meeting.ssafy.com/hooks/xxxxxxxx
```

서버는 다음 순서로 처리합니다.

1. 명령어를 실행한 사용자의 username을 확인합니다.
2. URL이 `https://meeting.ssafy.com/hooks/`로 시작하는 올바른 형식인지 검사합니다.
3. username과 Webhook URL을 `webhook_registry.json`에 저장합니다.
4. 등록 완료 메시지를 사용자에게 보여줍니다.

이미 등록된 사용자가 다시 `등록` 명령어를 실행하면 기존 값이 새로운 Webhook URL로 교체됩니다.

### DM 발송 방식

서버는 Incoming Webhook에 다음 형태의 데이터를 전송합니다.

```json
{
  "channel": "@target_username",
  "text": "보낼 메시지"
}
```

`channel`에 `@사용자명`을 지정하여 해당 사용자에게 DM을 보냅니다.

---

## 3. 프로젝트 파일

```text
mattermost_dm_bot/
├─ main.py                  # FastAPI 서버와 DM 공지 기능
├─ .env                     # Slash Command Token 저장
├─ webhook_registry.json    # 사용자가 등록한 Webhook URL 저장
├─ .gitignore               # Git에 올리지 않을 파일 목록
├─ README.md                # 프로젝트 사용 설명서
└─ venv/                    # Python 가상환경
```

### `.env`

서버 공통 설정인 `SLASH_COMMAND_TOKEN`을 저장합니다.

개인별 Webhook URL은 더 이상 `.env`에 작성하지 않습니다.

### `webhook_registry.json`

사용자가 `/dm 등록 ...` 명령어로 등록한 정보가 자동으로 저장됩니다.

구조는 다음과 같습니다.

```json
{
  "users": {
    "hong.gildong": {
      "webhook_url": "https://meeting.ssafy.com/hooks/xxxxxxxx",
      "registered_at": "2026-06-11T10:30:00"
    }
  }
}
```

- `hong.gildong`: 명령어를 실행한 사용자의 Mattermost username
- `webhook_url`: 사용자가 등록한 Incoming Webhook URL
- `registered_at`: 등록 또는 마지막 변경 시각

사용자가 처음 등록하면 항목이 추가되고, 다시 등록하면 같은 username의 정보가 갱신됩니다. `등록삭제` 명령어를 사용하면 해당 사용자의 항목이 삭제됩니다.

이 파일에는 실제 Webhook URL이 들어 있으므로 외부에 공유하거나 Git에 올리면 안 됩니다. 현재 `.gitignore`에는 `webhook_registry.json`이 등록되어 있습니다.

---

## 4. 사전 준비

운영자에게 필요한 항목:

1. Python
2. 이 프로젝트 폴더
3. ngrok
4. Mattermost Slash Command 생성 권한
5. 서버 실행 권한

DM 공지 사용자를 위해 필요한 항목:

1. Mattermost 계정
2. Incoming Webhook 생성 권한

Mattermost에서 통합 기능이 보이지 않는다면 시스템 관리자에게 Incoming Webhook 또는 Slash Command 생성 권한을 요청해야 합니다.

---

## 5. 패키지 설치

PowerShell에서 프로젝트 폴더로 이동합니다.

```powershell
cd C:\Users\SSAFY\Desktop\mattermost_dm_bot
```

가상환경을 활성화합니다.

```powershell
.\venv\Scripts\Activate.ps1
```

터미널 앞에 `(venv)`가 표시되면 활성화된 것입니다.

실행 정책 오류가 발생하면 다음 명령어를 한 번 실행한 뒤 다시 활성화합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

필요한 패키지를 설치합니다.

```powershell
pip install fastapi uvicorn python-dotenv requests python-multipart
```

이미 설치되어 있다면 다시 설치하지 않아도 됩니다.

---

## 6. `.env` 작성 방법

`.env` 파일은 프로젝트 최상위 폴더에 둡니다.

현재 필요한 설정은 다음과 같습니다.

```env
SLASH_COMMAND_TOKEN=Mattermost에서_복사한_토큰
```

`SLASH_COMMAND_TOKEN`은 요청이 등록된 Mattermost Slash Command에서 온 것인지 검사하는 값입니다.

Mattermost의 Slash Command 설정 화면에서 Token을 복사하여 `=` 뒤에 붙여 넣습니다.

```env
SLASH_COMMAND_TOKEN=abcdefghijklmnopqrstuvwxyz
```

토큰 검사를 사용하지 않으려면 값을 비울 수 있습니다.

```env
SLASH_COMMAND_TOKEN=
```

보안을 위해 실제 운영 환경에서는 토큰을 설정하는 것을 권장합니다. `.env`를 변경한 경우에는 uvicorn 서버를 다시 시작해야 적용됩니다.

> 개인별 Incoming Webhook URL은 `.env`에 작성하지 않습니다. 각 사용자가 Mattermost 명령어로 직접 등록합니다.

---

## 7. Mattermost Incoming Webhook 생성 방법

DM 공지 기능을 사용하려는 각 사용자는 본인 계정으로 Incoming Webhook을 하나 만들어야 합니다.

Mattermost 버전과 권한에 따라 메뉴 이름은 조금 다를 수 있습니다.

1. Mattermost에 로그인합니다.
2. 왼쪽 위의 팀 이름 또는 메뉴 버튼을 누릅니다.
3. `Integrations` 또는 `통합`을 선택합니다.
4. `Incoming Webhooks`를 선택합니다.
5. `Add Incoming Webhook` 또는 `Incoming Webhook 추가`를 누릅니다.
6. 이름을 입력합니다.

```text
DM 공지 봇 - 본인 이름
```

7. 설명을 입력합니다.

```text
개인 DM 공지 발송용 Webhook
```

8. 본인이 접근할 수 있는 기본 채널을 선택합니다.
9. 저장합니다.
10. 생성된 Webhook URL을 복사합니다.

Webhook URL은 다음과 비슷한 형태입니다.

```text
https://meeting.ssafy.com/hooks/xxxxxxxxxxxxxxxxxxxxxxxxxx
```

이 주소는 비밀번호처럼 취급해야 합니다. 채널, 문서, 캡처 화면 등에 공개하지 마세요.

---

## 8. 개인 Webhook 등록 방법

Incoming Webhook을 만든 사용자는 Mattermost 채팅창에서 다음 명령어를 실행합니다.

```text
/dm 등록 https://meeting.ssafy.com/hooks/본인의웹훅주소
```

예시:

```text
/dm 등록 https://meeting.ssafy.com/hooks/abc123xyz789
```

등록에 성공하면 본인에게 다음과 같은 완료 메시지가 표시됩니다.

```text
@사용자명님의 Webhook URL 등록이 완료되었습니다.
이제 /dm @대상자 메시지 형식으로 사용할 수 있습니다.
```

등록 정보는 즉시 `webhook_registry.json`에 저장되므로 서버를 재시작할 필요가 없습니다.

### 등록 가능한 URL

현재 서버는 보안을 위해 다음 조건을 모두 만족하는 URL만 허용합니다.

- `https` 주소
- 도메인이 정확히 `meeting.ssafy.com`
- 경로가 `/hooks/`로 시작함

따라서 다른 도메인, `http` 주소, 일반 채널 주소는 등록되지 않습니다.

### 기존 URL 변경

Webhook을 새로 만들었거나 URL을 바꾸려면 새 주소로 다시 등록합니다.

```text
/dm 등록 https://meeting.ssafy.com/hooks/새로운웹훅주소
```

기존 등록값은 새로운 값으로 자동 교체됩니다.

---

## 9. 등록 확인 및 삭제

### 등록 확인

본인의 Webhook URL이 등록되어 있는지 확인하려면 다음 명령어를 사용합니다.

```text
/dm 등록확인
```

보안을 위해 응답에는 Webhook URL 전체가 아닌 일부만 가려진 형태로 표시됩니다.

### 등록 삭제

더 이상 DM 공지 봇을 사용하지 않거나 Webhook URL을 폐기하려면 다음 명령어를 실행합니다.

```text
/dm 등록삭제
```

이 명령어를 실행하면 `webhook_registry.json`에서 본인의 등록 정보가 삭제됩니다.

Mattermost에서 Incoming Webhook 자체도 더 이상 사용하지 않을 예정이라면 Mattermost의 `Integrations` 메뉴에서도 해당 Webhook을 삭제하세요.

### 도움말

명령어가 기억나지 않으면 다음 중 하나를 입력합니다.

```text
/dm
/dm 도움말
/dm help
```

---

## 10. DM 공지 보내기

먼저 본인의 Webhook URL을 등록한 뒤 다음 형식으로 사용합니다.

```text
/dm @받는사람1 @받는사람2 보낼 메시지
```

예시:

```text
/dm @user1 @user2 오늘 14시까지 출결 사유를 입력해 주세요.
```

위 명령어는 다음과 같이 처리됩니다.

```text
받는 사람: @user1, @user2
메시지: 오늘 14시까지 출결 사유를 입력해 주세요.
```

같은 대상자를 여러 번 입력해도 한 번만 발송됩니다.

```text
/dm @user1 @user1 @user2 회의가 시작됩니다.
```

실제 발송 대상은 `@user1`, `@user2` 두 명입니다.

발송이 끝나면 명령어를 실행한 본인에게 성공 인원, 실패 인원, 성공 대상과 실패 대상이 표시됩니다.

---

## 11. 사용자 추가 방법

이제 운영자가 `.env`에 사용자를 추가할 필요가 없습니다.

새 사용자는 아래 과정만 직접 진행하면 됩니다.

1. 본인 Mattermost 계정으로 Incoming Webhook을 생성합니다.
2. 생성된 URL을 복사합니다.
3. Mattermost 채팅창에서 등록 명령어를 실행합니다.

```text
/dm 등록 https://meeting.ssafy.com/hooks/본인의웹훅주소
```

4. 등록 여부를 확인합니다.

```text
/dm 등록확인
```

5. DM 발송을 테스트합니다.

```text
/dm @테스트대상자 테스트 메시지입니다.
```

새 사용자 등록 때문에 uvicorn이나 ngrok을 재시작할 필요는 없습니다.

---

## 12. Mattermost Slash Command 생성 방법

Slash Command는 운영자가 한 번 생성합니다. 일반 사용자는 같은 `/dm` 명령어를 함께 사용합니다.

1. Mattermost에 로그인합니다.
2. 팀 이름 또는 메뉴를 누릅니다.
3. `Integrations` 또는 `통합`으로 이동합니다.
4. `Slash Commands`를 선택합니다.
5. `Add Slash Command`를 누릅니다.
6. 다음 내용을 입력합니다.

```text
Title: DM 공지 봇
Description: 개인 Webhook을 등록하고 여러 사용자에게 DM 공지를 보냅니다.
Command Trigger Word: dm
Request URL: https://ngrok주소/mattermost/dm-broadcast
Request Method: POST
Response Username: DM 공지 봇
Autocomplete: 활성화
Autocomplete Hint: 등록 URL | 등록확인 | 등록삭제 | @user1 @user2 메시지
Autocomplete Description: Webhook 등록 및 다중 DM 공지 발송
```

7. 저장합니다.
8. 생성된 Token 값을 복사합니다.
9. `.env`의 `SLASH_COMMAND_TOKEN`에 입력합니다.
10. `.env`를 변경했다면 uvicorn 서버를 재시작합니다.

Request URL 끝에는 반드시 `/mattermost/dm-broadcast`가 있어야 합니다.

---

## 13. uvicorn 서버 켜기

PowerShell에서 다음 명령어를 실행합니다.

```powershell
cd C:\Users\SSAFY\Desktop\mattermost_dm_bot
.\venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```

개발 중 코드 변경을 자동 반영하려면 다음과 같이 실행할 수 있습니다.

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

정상 실행되면 다음과 비슷한 메시지가 보입니다.

```text
Uvicorn running on http://0.0.0.0:8000
```

브라우저에서 다음 주소를 열어 서버 상태를 확인할 수 있습니다.

```text
http://localhost:8000/
```

정상 상태라면 다음과 비슷한 JSON이 표시됩니다.

```json
{
  "status": "ok",
  "service": "mattermost-dm-broadcast"
}
```

uvicorn이 실행되는 터미널은 계속 켜 두어야 합니다.

---

## 14. uvicorn 서버 끄기

uvicorn을 실행한 터미널에서 다음 키를 누릅니다.

```text
Ctrl + C
```

`.env`를 수정했거나 서버를 다시 시작해야 한다면 종료 후 다음 명령어를 다시 실행합니다.

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

사용자의 Webhook 등록, 변경, 삭제는 즉시 JSON 파일에 저장되므로 해당 작업만으로는 서버를 재시작할 필요가 없습니다.

---

## 15. ngrok 켜기

Mattermost가 로컬 FastAPI 서버에 접근하려면 외부 HTTPS 주소가 필요합니다.

1. uvicorn 서버를 먼저 실행합니다.
2. 새로운 PowerShell 창을 엽니다.
3. ngrok을 실행합니다.

ngrok이 PATH에 등록되어 있다면:

```powershell
ngrok http 8000
```

ngrok이 `C:\ngrok`에 있다면:

```powershell
C:\ngrok\ngrok.exe http 8000
```

정상 실행되면 다음과 비슷한 주소가 표시됩니다.

```text
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Mattermost Slash Command의 Request URL에는 다음과 같이 입력합니다.

```text
https://abc123.ngrok-free.app/mattermost/dm-broadcast
```

무료 ngrok 주소는 다시 실행할 때 변경될 수 있습니다. 주소가 바뀌었다면 Mattermost Slash Command의 Request URL도 새 주소로 수정해야 합니다.

---

## 16. ngrok 끄기

ngrok을 실행한 터미널에서 다음 키를 누릅니다.

```text
Ctrl + C
```

ngrok이 종료되면 Mattermost에서 로컬 서버에 접근할 수 없으므로 `/dm` 명령어도 동작하지 않습니다.

---

## 17. 전체 실행 순서

### 운영자 최초 설정

1. 프로젝트의 Python 패키지를 설치합니다.
2. Mattermost Slash Command를 생성합니다.
3. Slash Command Token을 `.env`에 작성합니다.
4. uvicorn 서버를 실행합니다.
5. ngrok을 실행합니다.
6. ngrok 주소를 Slash Command의 Request URL에 입력합니다.
7. 브라우저와 Mattermost에서 동작을 확인합니다.

### 서버를 다시 켤 때

첫 번째 PowerShell:

```powershell
cd C:\Users\SSAFY\Desktop\mattermost_dm_bot
.\venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```

두 번째 PowerShell:

```powershell
ngrok http 8000
```

ngrok 주소가 변경되었다면 Slash Command의 Request URL을 갱신합니다.

### 일반 사용자가 처음 사용할 때

```text
1. Mattermost에서 본인의 Incoming Webhook 생성
2. /dm 등록 https://meeting.ssafy.com/hooks/본인의웹훅주소
3. /dm 등록확인
4. /dm @대상자 테스트 메시지
```

---

## 18. Mattermost username 확인 방법

DM 대상자 지정에는 표시 이름이 아닌 Mattermost username을 사용합니다.

예를 들어 화면의 표시 이름이 `홍길동`이어도 username은 `hong.gildong`일 수 있습니다.

1. Mattermost에서 사용자의 프로필을 누릅니다.
2. 프로필에 표시되는 `@username`을 확인합니다.
3. DM 명령어에 동일한 값을 입력합니다.

```text
/dm @hong.gildong 메시지 내용
```

본인의 Webhook 등록 정보는 명령어 요청에 포함된 username을 기준으로 서버가 자동 저장하므로 등록 명령어에 본인 username을 따로 입력할 필요가 없습니다.

---

## 19. 자주 발생하는 문제

### Webhook URL이 등록되어 있지 않다고 나오는 경우

본인의 Webhook URL을 아직 등록하지 않았거나 등록을 삭제한 상태입니다.

```text
/dm 등록 https://meeting.ssafy.com/hooks/본인의웹훅주소
```

등록 후 다음 명령어로 확인합니다.

```text
/dm 등록확인
```

### Webhook URL 형식이 올바르지 않다고 나오는 경우

현재 코드는 `https://meeting.ssafy.com/hooks/` 형식만 허용합니다.

확인할 내용:

1. URL 앞뒤에 불필요한 문자가 없는지 확인합니다.
2. `http://`가 아닌 `https://`인지 확인합니다.
3. 도메인이 정확히 `meeting.ssafy.com`인지 확인합니다.
4. 주소에 `/hooks/`가 포함되어 있는지 확인합니다.

### 대상자를 찾지 못했다고 나오는 경우

대상자를 `@username` 형식으로 입력해야 합니다.

```text
/dm @user1 @user2 메시지
```

### 보낼 메시지가 없다고 나오는 경우

대상자 뒤에 실제 메시지를 작성해야 합니다.

잘못된 예:

```text
/dm @user1 @user2
```

올바른 예:

```text
/dm @user1 @user2 오늘 14시까지 제출해 주세요.
```

### Slash Command Token 오류가 나오는 경우

Mattermost Slash Command의 Token과 `.env`의 `SLASH_COMMAND_TOKEN`이 다른 경우입니다.

1. Mattermost Slash Command 설정에서 Token을 다시 복사합니다.
2. `.env` 값을 수정합니다.
3. uvicorn 서버를 재시작합니다.

### 명령어가 응답하지 않는 경우

1. uvicorn이 실행 중인지 확인합니다.
2. 브라우저에서 `http://localhost:8000/`에 접속합니다.
3. ngrok이 실행 중인지 확인합니다.
4. Slash Command의 Request URL이 최신 ngrok 주소인지 확인합니다.
5. Request URL 끝에 `/mattermost/dm-broadcast`가 있는지 확인합니다.

### 등록 정보가 사라진 경우

등록 정보는 프로젝트 폴더의 `webhook_registry.json`에 저장됩니다.

확인할 내용:

1. 서버가 항상 같은 프로젝트 폴더에서 실행되는지 확인합니다.
2. `webhook_registry.json`이 삭제되지 않았는지 확인합니다.
3. 서버를 다른 컴퓨터나 폴더로 옮겼다면 기존 JSON 파일도 함께 옮겼는지 확인합니다.

---

## 20. 보안 및 운영 주의사항

### Webhook URL 보호

Incoming Webhook URL을 아는 사람은 해당 Webhook을 이용할 수 있으므로 비밀번호처럼 관리해야 합니다.

- Webhook URL을 공개 채널에 올리지 않습니다.
- 등록 명령어는 다른 사람이 볼 수 없는 DM 또는 안전한 채널에서 실행하는 것을 권장합니다.
- 화면 캡처나 문서에 실제 URL을 노출하지 않습니다.
- URL이 노출되었다면 Mattermost에서 기존 Webhook을 삭제하고 새로 만듭니다.

### 민감한 파일

다음 파일은 외부 저장소에 올리거나 공유하면 안 됩니다.

```text
.env
webhook_registry.json
```

두 파일은 `.gitignore`에 포함되어 있는지 항상 확인하세요.

### 등록 정보 백업

`webhook_registry.json`이 삭제되면 모든 사용자가 다시 등록해야 합니다. 서버 이전이나 백업 작업을 할 때는 이 파일을 안전하게 보관해야 합니다.

백업 파일에도 실제 Webhook URL이 포함되므로 접근 권한을 제한하세요.

### 서버 실행 조건

로컬 운영 시 아래 두 프로그램이 모두 실행 중이어야 합니다.

```text
uvicorn: FastAPI 앱 실행
ngrok: Mattermost가 접속할 외부 HTTPS 주소 제공
```

둘 중 하나라도 종료되면 Slash Command가 동작하지 않습니다.

사용자 Webhook 등록은 서버 재시작 없이 즉시 적용됩니다. `.env` 변경이나 Python 코드 변경은 uvicorn 재시작이 필요합니다.
