# instruction-impact

**AI 코딩 지침을 바꾸면, 코드가 그대로여도 영향을 받는 파일이 생깁니다. 그 범위를 Git 커밋 두 개로 비교하는 도구입니다.**

예를 들어 `api/AGENTS.md`에서 “트랜잭션을 사용하세요”를 “트랜잭션과 감사 로그를 사용하세요”로 바꾸면, `api/` 아래 소스 파일들의 지침이 달라집니다. 일반 Git diff에는 지침 파일만 나오지만, 이 도구는 **수정하지 않은 소스 파일까지** 찾아줍니다. `apiary/`처럼 이름만 비슷한 형제 폴더는 포함하지 않습니다.

## 설치·실행

Python 3.10 이상, Git 2.20 이상이 필요합니다. PyPI에는 아직 배포하지 않았습니다.

```sh
pip install "git+https://github.com/deploy103/instruction-impact.git"

# 분석할 저장소 안에서 실행
instruction-impact HEAD~1
instruction-impact main HEAD --format json
instruction-impact main HEAD --format markdown > impact.md
instruction-impact main HEAD --fail-on-change
```

- 텍스트·JSON·Markdown 출력
- 상위 폴더부터 해당 파일의 폴더까지 지침 출처와 변경 내용 비교
- API 키, LLM, 런타임 외부 패키지 불필요
- Git에 저장된 객체만 읽으며, 저장소 코드나 지침의 명령을 실행하지 않음
- 종료 코드: 기본 성공 0 / 지침 변경 감지 옵션 사용 시 1 / 오류 2

## 한계

정확히 `AGENTS.md`라는 이름의 **커밋된 지침 파일**만 분석합니다. 미커밋 변경, `AGENTS.override.md`, `CLAUDE.md`, 홈 폴더 지침, 에이전트 설정·토큰 제한·자연어 충돌 해석은 제외합니다. 따라서 특정 AI가 실제로 받은 프롬프트를 재현하거나 보안성을 보증하는 도구는 아닙니다. 지침 심볼릭 링크는 오류로 처리합니다.

완전히 최초인 아이디어라는 주장도 하지 않습니다. 조사한 관련 프로젝트와 차이점은 [조사 문서](docs/research.md)에 기록했습니다.

## 재현 가능한 데모·테스트

```sh
git clone https://github.com/deploy103/instruction-impact.git
cd instruction-impact
python -m pip install .
python examples/demo.py
python -m unittest discover -s tests -v
```

데모는 임시 Git 저장소에서 실제 커밋 두 개를 만들고 결과를 출력한 다음 임시 저장소를 삭제합니다.

## OpenAI 오픈소스 지원에 관하여

이 프로젝트는 OpenAI의 공식 프로젝트가 아니며 지원 프로그램에 선정된 프로젝트도 아닙니다. [Codex for Open Source](https://developers.openai.com/community/codex-for-oss)는 선정된 오픈소스 유지관리자에게 Pro 6개월 등을 지원하는 프로그램입니다. 새 공개 저장소를 만들었다고 자동 선정되지 않으며, 실제 사용성과 생태계 기여를 정직하게 설명해야 합니다.

세부 동작과 기여 방법은 [영문 README](README.md)를 참고하세요. MIT 라이선스입니다.
