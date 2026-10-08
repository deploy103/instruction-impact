# instruction-impact · AI 지침 변경 영향 분석

### 지침 파일의 diff를 파일별 적용 범위와 리뷰 근거로 바꿉니다.

[![Tests](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml/badge.svg)](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-blue)](pyproject.toml)

[영문 문서](README.md) · [분석 모델과 신뢰 경계](docs/design.md) · [JSON 명세](docs/json.md) · [기존 도구 조사](docs/research.md)

**Git 기반 분석 · Codex 선택 규칙 · 파일별 원인 추적 · CI 리뷰 게이트 · 버전 관리되는 JSON**

PR에서 `services/payments/AGENTS.md`의 “단위 테스트를 실행하세요”를 “자동 생성한 변경은 테스트를 생략하세요”로 바꿨다고 가정해 보겠습니다. Git diff에는 Markdown 파일 하나만 나옵니다. 하지만 리뷰어에게 필요한 질문은 다릅니다.

**이 변경으로 어떤 파일들이 다른 지침을 물려받게 되는가? 그중 실제 코드 변경 목록에 없는 파일은 무엇인가?**

`instruction-impact`는 두 Git 커밋의 지침 출처를 비교해서 이 질문에 답합니다. 단순히 지침 파일을 찾는 것이 아니라, 변경된 파일의 선택 상태, 적용 범위, 파일별 변경 원인, 상위→하위 출처 체인을 함께 보여줍니다. Git과 Python만 필요하며 AI 호출·API 키·세션 수집이 없습니다.

## 이런 작업에 사용합니다

| 작업 | 제공하는 근거 |
| --- | --- |
| 모노레포의 지침 변경 리뷰 | 실제 하위 경로와 수정되지 않은 코드의 출처 변경 |
| override 도입·삭제 검토 | 선택됨·가려짐·빈 지침 상태와 적용 체인 |
| PR 자동 검사 | 공통 조상 비교, job summary, 완전한 JSON, 정책 판단용 영향 개수 |
| 사내 리뷰 도구 연동 | AI 서비스 없이 스키마가 정의된 데이터와 전체 Git 객체 ID |
| 리뷰 증거 보관 | 한 번의 분석으로 생성한 JSON·Markdown 보고서 묶음 |

## 기술 스택

호스팅 웹 서비스가 아니라 로컬 분석 파이프라인입니다. 별도의 프론트엔드 프레임워크, 데이터베이스, 메시지 큐, 모델 서버가 필요하지 않습니다.

| 계층 | 기술 | 역할 |
| --- | --- | --- |
| 실행 환경 | Python 3.10+, 표준 라이브러리 | CLI, 지침 선택, 출처 비교, 보고서 생성 |
| 저장소 접근 | Git CLI: `rev-parse`, `merge-base`, `ls-tree`, `cat-file` | 체크아웃 없이 커밋된 트리와 지침 blob 읽기 |
| 인터페이스 | `argparse`, Python API, JSON, Markdown | 사용자 명령, 자동화, 리뷰 산출물 |
| 데이터 계약 | JSON Schema Draft 2020-12 | 스키마 버전 2 검증; 런타임 검증 라이브러리는 불필요 |
| CI 연동 | GitHub Actions composite Action, Bash | 읽기 전용 PR 분석과 job summary |
| 패키징 | `pyproject.toml`, Hatchling | 설치 가능한 CLI, wheel, 소스 배포본 |
| 회귀 테스트 | `unittest`, 실제 임시 Git 저장소, `jsonschema` | 선택 규칙, CLI, Action 스크립트, 출력 계약 |
| 코드 품질 | Ruff | 린트와 포맷 검사 |
| 호환성 CI | Ubuntu, Python 3.10 / 3.12 / 3.14 | 테스트, 데모, Action, 패키징 검사 |

### 처리 흐름

```text
base / head / 선택 프로필
          ↓
커밋 확정 + 선택적 merge-base 계산
          ↓
Git 트리 + 중복 제거된 지침 blob 읽기
          ↓
각 디렉터리의 기여 지침 선택
          ↓
상위→하위 출처 체인 비교 + 변경 원인 연결
          ↓
텍스트 / Markdown / 버전 관리되는 JSON
          ↓
CLI 게이트 / 보고서 묶음 / CI summary
```

일반 소스 코드 내용을 읽거나 실행하지 않습니다. 지침 blob과 디렉터리별 체인을 캐시하고, 텍스트 표현이 아니라 전체 객체 ID로 변경 여부를 판단합니다. 사람이 보는 목록을 줄여도 JSON에는 전체 결과가 유지됩니다.

## 일반적인 diff와 무엇이 다른가

```text
AGENTS.md                 전체 저장소 지침
api/AGENTS.md             API 서비스 지침 ← 이번 PR에서 변경
api/auth.py               코드는 그대로
api/deep/model.py         코드는 그대로
apiary/sibling.py          비슷한 이름이지만 다른 범위
```

`api/AGENTS.md` 변경은 `auth.py`, `model.py`의 출처 체인을 바꿉니다. `apiary/sibling.py`는 영향을 받지 않습니다. 보고서는 수정되지 않은 두 파일을 `[unchanged]`로 표시하고, 어떤 지침이 달라졌는지 연결합니다.

Codex에서는 더 미묘한 경우가 있습니다. 같은 폴더에 `AGENTS.override.md`가 있으면 일반 `AGENTS.md`는 선택되지 않습니다. 따라서 일반 파일을 고쳐도 적용 체인은 그대로일 수 있습니다. 반대로 **빈 override를 추가하면 일반 지침이 차단됩니다.** 빈 파일이라고 영향이 없는 것은 아닙니다. 이 규칙은 Codex 구현을 확인해 반영했습니다.

## 실제 커밋으로 먼저 확인하기

Python 3.10 이상과 최신 Git이 필요합니다. 데모·테스트는 Git 2.28 이상에서 지원하는 `git init -b`를 사용합니다.

```sh
git clone https://github.com/deploy103/instruction-impact.git
cd instruction-impact
python -m venv .venv
. .venv/bin/activate
python -m pip install .

python examples/demo.py
python examples/demo.py --scenario override --format markdown
python examples/demo.py --scenario shadowed
python examples/demo.py --scenario empty-override
python examples/demo.py --scenario fallback --format json
```

데모는 임시 저장소에 커밋 두 개를 만들고 분석한 다음 삭제합니다. `shadowed`에서는 지침 변경 1건·영향 파일 0건, 나머지 시나리오에서는 수정하지 않은 파일 2개의 적용 출처 변경을 확인할 수 있습니다. CI가 이 경로 목록과 JSON 스키마를 실제 출력으로 검사합니다.

직접 Git diff와 대조하려면 새 폴더에 fixture를 남길 수 있습니다. 기존 폴더를 덮어쓰지는 않습니다.

```sh
python examples/demo.py --scenario empty-override --write-repo /tmp/instruction-fixture
git -C /tmp/instruction-fixture diff HEAD~1 HEAD
instruction-impact HEAD~1 HEAD --repo /tmp/instruction-fixture --profile codex
```

## 자신의 저장소에서 사용하기

PyPI에는 아직 배포하지 않았습니다. GitHub에서 설치하거나 위와 같이 로컬 설치하세요. 자동화에서는 검토한 커밋으로 설치 버전을 고정하는 것이 좋습니다.

```sh
python -m pip install "git+https://github.com/deploy103/instruction-impact.git"

# 분석할 저장소 안에서 실행
instruction-impact HEAD~1
instruction-impact origin/main HEAD --merge-base --profile codex
instruction-impact origin/main HEAD --merge-base --format markdown > impact.md
instruction-impact origin/main HEAD --merge-base --format json > impact.json

# 같은 분석 결과의 JSON·Markdown을 함께 저장; 새 경로를 사용하세요.
instruction-impact origin/main HEAD --merge-base --profile codex \
  --output-dir review-artifacts/pr-123 --fail-on-impact
```

`--output-dir`은 UTF-8 `report.json`, `report.md`를 생성합니다. stdout 형식은 여전히 `--format`으로 정합니다. 영향 게이트가 종료 코드 1을 반환하기 전에 보고서를 저장하므로 리뷰가 차단돼도 근거는 남습니다. 기존 디렉터리는 덮어쓰지 않고 종료 코드 2로 거부하며, 필요한 부모 디렉터리는 생성합니다. 파일 저장은 트랜잭션이 아니므로 I/O 오류가 발생하면 일부 파일만 남을 수 있습니다. 오류를 해결한 뒤 새 경로를 사용하세요. 보고서에 비공개 지침이 포함될 수 있습니다.

PR에서는 `--merge-base`를 쓰면 대상 브랜치에만 들어간 변경을 PR의 변경으로 잘못 해석하지 않습니다. 두 커밋과 공통 조상이 로컬에 있어야 하며, CI에서는 `fetch-depth: 0` 또는 필요한 이력을 명시적으로 가져오세요. 체크아웃을 바꾸거나 미커밋·스테이징 변경을 포함하지 않습니다.

### 프로필은 명시적으로 선택

| 항목 | 기본 `agents` | `codex` |
| --- | --- | --- |
| 후보 지침 | `AGENTS.md` | override → 일반 → 설정한 fallback |
| 폴더당 선택 | `AGENTS.md` | 먼저 존재하는 후보 하나 |
| 빈 파일 | 출처 존재로 유지 | 선택되지만 내용은 제외; 다음 후보를 재선택하지 않음 |
| 상위 지침 | 하위 지침과 함께 누적 | 하위 지침과 함께 누적 |

```sh
instruction-impact main HEAD --profile codex \
  --fallback TEAM_GUIDE.md --fallback .agents.md
```

fallback은 입력 순서가 우선순위입니다. 홈 폴더의 Codex 설정을 몰래 읽지 않으며, 명시한 후보 목록을 JSON에 남깁니다.

### CI에서 무엇을 실패시킬지 선택

- `--fail-on-change`: 선택되지 않은 지침까지 포함해 후보 파일의 내용·존재 변경이 있으면 1.
- `--fail-on-impact`: **기존 파일**의 적용 출처 체인이 바뀔 때만 1. 코드 파일 추가·삭제만으로는 실패하지 않음.
- 옵션 없이는 보고서 생성 성공 0. 인자·Git·지원하지 않는 지침 항목 등의 오류는 2.

두 실패 옵션은 동시에 사용할 수 없습니다. 실패 판정 전에 보고서를 출력하므로 원인을 확인할 수 있습니다.

텍스트는 기본 20개 파일까지, Markdown은 각 지침 목록도 20개까지 보여주고 생략 수를 표시합니다. `--max-files`로 조절할 수 있으며 **JSON에는 항상 전체 결과가 들어갑니다.**

## GitHub Actions에서 팀이 검토할 보고서 만들기

재사용 가능한 composite Action도 제공합니다. PR의 두 커밋을 공통 조상 기준으로 비교해 job summary와 Markdown·JSON 파일을 만듭니다. 분석 대상의 패키지를 설치하거나 코드를 실행하지 않고, 댓글 게시·쓰기 권한도 요구하지 않습니다.

```yaml
- uses: actions/checkout@v5
  with:
    fetch-depth: 0
    persist-credentials: false
- uses: actions/setup-python@v6
  with:
    python-version: '3.12'
- uses: deploy103/instruction-impact@main # 실사용에서는 검토한 전체 커밋 SHA로 고정
  id: impact
  with:
    base: ${{ github.event.pull_request.base.sha }}
    head: ${{ github.event.pull_request.head.sha }}
    profile: codex
    max-files: '30'
    fallback: |
      TEAM_GUIDE.md
      .agents.md
```

Action은 Bash·Python 3.11 이상이 필요합니다. 한 번의 분석으로 두 보고서를 생성하며, 영향이 있다는 이유만으로 Action 자체가 실패하지는 않습니다. 출력 `report-path`, `json-path`, `existing-files-affected`를 artifact 업로드나 정책 검사에 사용할 수 있습니다. `max-files`의 기본값은 20이며 JSON은 줄이지 않습니다. `fallback`은 한 줄에 파일 이름 하나씩 우선순위 순서로 지정하고, 빈 줄은 무시합니다. 공백이 있는 이름도 그대로 전달하며, fallback을 지정하면 `codex` 프로필이 필요합니다. 완전한 workflow는 [영문 README](README.md#github-action-a-report-not-privileged-pr-automation)에 있습니다.

보고서에는 지침 내용이 들어갑니다. 비공개 저장소라면 summary·artifact의 공개 범위를 먼저 확인하세요. 신뢰할 수 없는 PR 코드를 `pull_request_target`에서 실행하는 방식은 사용하지 마세요.

## 약속하는 것과 약속하지 않는 것

이 도구는 **커밋된 저장소 안에서 지침 출처가 달라졌다는 근거**를 제공합니다. 특정 AI의 실제 프롬프트·행동을 재현하거나 보안을 인증하지 않습니다.

홈 지침, 세션의 현재 작업 폴더, 사용자 대화, Codex의 바이트 제한, 문장 간 충돌 해석은 범위 밖입니다. 지침 심볼릭 링크는 따라가지 않고 오류로 처리하며, 서브모듈 내부도 탐색하지 않습니다. 파일 이름 변경은 삭제+추가로 표시합니다. 텍스트 diff는 줄바꿈을 정규화한 리뷰용이며, 적용 가능한 Git 패치가 아닙니다.

일반 Git 설정과 실행 파일을 신뢰하는 로컬 도구이지 별도의 샌드박스는 아닙니다. 전체 트리 메타데이터와 결과를 메모리에 유지하므로, 출력 개수 제한을 자원 제한이라고 주장하지 않습니다. 자세한 판단 기준과 호환성 차이는 [설계 문서](docs/design.md)에 기록했습니다.

## 유지관리와 기여

### 프로젝트 구조

```text
src/instruction_impact/
  core.py                 Git 스냅샷, 선택 규칙, 출처 변경과 원인 분석
  report.py               안전한 텍스트·Markdown 출력
  cli.py                  명령 옵션, 보고서 묶음, 종료 정책
action.yml                읽기 전용 GitHub Actions 연동
tests/test_impact.py       실제 Git 회귀 테스트와 Action Bash 실행 검증
tests/check_schema.py     데모 출력 스키마와 독립적인 예상 경로 검사
examples/demo.py          재현 가능한 두 커밋 시나리오 5개
docs/                     설계, JSON 계약·스키마, 관련 도구 조사
.github/workflows/        호환성·린트·Action·패키징 검사
```

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
```

실제 임시 Git 저장소 기반 회귀 테스트, 5개 데모의 JSON 스키마·예상 경로 검사, Python 3.10·3.12·3.14 CI, composite Action 출력 검증을 제공합니다. 구현은 분석·출력·CLI 정책으로 책임을 나누며 런타임 의존성은 없습니다.

기여할 때는 “성공했다”는 사례보다 **틀린 구현이 실패하는 반례**를 추가해 주세요. `api/`와 `apiary/`, 빈 override와 삭제한 override, 지침 변경과 코드 추가를 구분하는 입력이 좋은 예입니다. [기여 가이드](CONTRIBUTING.md), [변경 이력](CHANGELOG.md)을 참고하세요.

### 앞으로의 방향

0.3 개발 버전은 보고서 묶음과 Action 설정을 보강하며 JSON 스키마 버전 2는 유지합니다. 아직 초기 프로젝트이며, 실제 사용 사례를 바탕으로 유지관리하는 것이 목표입니다.

바이트 예산 모델링에는 명시적인 세션 모델, 스테이징·작업 트리 분석에는 별도 스냅샷 계약, 대형 모노레포 성능 주장에는 재현 가능한 측정이 필요합니다. 이는 향후 검토 방향이지 현재 제공하는 기능이 아닙니다. 새 에이전트 프로필은 실제 구현 근거와 반례 테스트를 갖춘 경우에만 추가합니다.

전 세계 최초라는 주장이나 OpenAI 지원 선정 보장은 하지 않습니다. OpenAI와 무관한 MIT 라이선스 프로젝트입니다. 지원 프로그램 사실 확인과 관련 도구 비교는 [조사 문서](docs/research.md)에 분리해 두었습니다.
