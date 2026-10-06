# instruction-impact

## 코드가 그대로인데, AI의 작업 지침은 달라졌다면?

[영문 문서](README.md) · [분석 모델과 신뢰 경계](docs/design.md) · [JSON 명세](docs/json.md) · [기존 도구 조사](docs/research.md)

PR에서 `services/payments/AGENTS.md`의 “단위 테스트를 실행하세요”를 “자동 생성한 변경은 테스트를 생략하세요”로 바꿨다고 가정해 보겠습니다. Git diff에는 Markdown 파일 하나만 나옵니다. 하지만 리뷰어에게 필요한 질문은 다릅니다.

**이 변경으로 어떤 파일들이 다른 지침을 물려받게 되는가? 그중 실제 코드 변경 목록에 없는 파일은 무엇인가?**

`instruction-impact`는 두 Git 커밋의 지침 출처를 비교해서 이 질문에 답합니다. 단순히 지침 파일을 찾는 것이 아니라, 변경된 파일의 선택 상태, 적용 범위, 파일별 변경 원인, 상위→하위 출처 체인을 함께 보여줍니다. Git과 Python만 필요하며 AI 호출·API 키·세션 수집이 없습니다.

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
```

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
```

Action은 Bash·Python 3.11 이상이 필요합니다. 출력 `report-path`, `json-path`, `existing-files-affected`를 artifact 업로드나 정책 검사에 사용할 수 있습니다. 완전한 workflow는 [영문 README](README.md#github-action-a-report-not-privileged-pr-automation)에 있습니다. fallback 후보 지정은 현재 CLI에서만 지원합니다.

보고서에는 지침 내용이 들어갑니다. 비공개 저장소라면 summary·artifact의 공개 범위를 먼저 확인하세요. 신뢰할 수 없는 PR 코드를 `pull_request_target`에서 실행하는 방식은 사용하지 마세요.

## 약속하는 것과 약속하지 않는 것

이 도구는 **커밋된 저장소 안에서 지침 출처가 달라졌다는 근거**를 제공합니다. 특정 AI의 실제 프롬프트·행동을 재현하거나 보안을 인증하지 않습니다.

홈 지침, 세션의 현재 작업 폴더, 사용자 대화, Codex의 바이트 제한, 문장 간 충돌 해석은 범위 밖입니다. 지침 심볼릭 링크는 따라가지 않고 오류로 처리하며, 서브모듈 내부도 탐색하지 않습니다. 파일 이름 변경은 삭제+추가로 표시합니다. 텍스트 diff는 줄바꿈을 정규화한 리뷰용이며, 적용 가능한 Git 패치가 아닙니다.

일반 Git 설정과 실행 파일을 신뢰하는 로컬 도구이지 별도의 샌드박스는 아닙니다. 전체 트리 메타데이터와 결과를 메모리에 유지하므로, 출력 개수 제한을 자원 제한이라고 주장하지 않습니다. 자세한 판단 기준과 호환성 차이는 [설계 문서](docs/design.md)에 기록했습니다.

## 유지관리와 기여

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
```

실제 임시 Git 저장소 기반 회귀 테스트, 5개 데모의 JSON 스키마·예상 경로 검사, Python 3.10·3.12·3.14 CI, composite Action 출력 검증을 제공합니다. 구현은 분석·출력·CLI 정책으로 책임을 나누며 런타임 의존성은 없습니다.

기여할 때는 “성공했다”는 사례보다 **틀린 구현이 실패하는 반례**를 추가해 주세요. `api/`와 `apiary/`, 빈 override와 삭제한 override, 지침 변경과 코드 추가를 구분하는 입력이 좋은 예입니다. [기여 가이드](CONTRIBUTING.md), [변경 이력](CHANGELOG.md)을 참고하세요.

아직 초기 0.2 프로젝트입니다. 전 세계 최초라는 주장이나 OpenAI 지원 선정 보장은 하지 않습니다. OpenAI와 무관한 MIT 라이선스 프로젝트이며, 실제 사용 사례를 바탕으로 유지관리하는 것이 목표입니다. 지원 프로그램 사실 확인과 관련 도구 비교는 [조사 문서](docs/research.md)에 분리해 두었습니다.
