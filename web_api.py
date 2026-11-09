"""
웹사이트용 래퍼. Skills.py / Attribute.py는 수정하지 않고 그대로 읽어서 쓴다.

- describe_inputs(): Skills.py 윗부분(입력 변수 영역)을 읽어서 입력창으로 만들 목록을 JSON으로 돌려준다
- run_sim(overrides_json): 입력값을 덮어쓴 뒤 Skills.py를 실행하고 분석 결과를 JSON으로 돌려준다

새 분석을 추가하려면 analyze() 안에 계산을 넣고 결과 dict에 키를 추가하면 된다.
"""
import ast
import io
import json
import sys
import tokenize
import types

# ---------------------------------------------------------------------------------------------
# 0. 소스 읽기
# ---------------------------------------------------------------------------------------------
_SRC = {"skills": "", "attribute": ""}
_BANNER_STOP = "아래 코드 수정X"
_BANNER_TAIL = "아래부터 코드 수정 및 추가 가능"



# ---------------------------------------------------------------------------------------------
# 웹 화면 설정: Skills.py는 건드리지 않고, 화면에 무엇을 어떻게 보여 줄지만 여기서 정한다
# ---------------------------------------------------------------------------------------------
# 화면에 보여 주지 않는 변수 (게임에서 정해진 값이라 사용자가 바꿀 이유가 없다). 값은 Skills.py의 값을 그대로 쓴다
HIDDEN = {
    "BREAKER_GAP", "BREAKER_INTERVAL", "BREAKER_HITS", "VULKAN_GAP", "VULKAN_HOLD", "VULKAN_HITS",
    "INFANTRY_PRE", "INFANTRY_INTERVAL", "INFANTRY_HITS", "AURA_COOLDOWN", "AURA_EXCLUDE", "COMBAT_START",
    "BULLET_RELOAD", "BULLET_EMPTY_SKILLS", "PILE", "CDR_EXEMPT", "KAIN_HITS_PER_PREP", "KAIN_PREP_NEED",
    "UNION_TABLE", "ASCENT_DELAY", "ASCENT_TICKS", "ASCENT_PROFICIENCY",
    "ORIGIN_P1_LEN", "ORIGIN_P1_HITS", "ORIGIN_GAP", "ORIGIN_P2_F", "ORIGIN_P2_S", "ORIGIN_ACCEL_DURATION", "ORIGIN_ACCEL_CD_RANGE",
    "HECATE_INTERVAL", "HECATE_PARTICLES", "HECATE_FIRST", "HECATE_AURA", "STYX_DELAY", "STYX_HIT_AT",
    "PHLEG_DELAY", "PHLEG_T1", "PHLEG_T2", "PHLEG_T2_N", "PHLEG_T3", "PHLEG_T3_N",
}

# 어센트에 적용되지 않는 장비 입력칸 (Skills.py의 gear_stat() 인자와 같은 이름). (제목, [(변수, 화면 이름), ...])
GEAR_ITEMS = ("Hat", "Ring_1", "Ring_2", "Ring_3")
GEAR_BASE = [("main", "주스탯"), ("sub", "부스탯"), ("all_pct", "올스탯 %"), ("attack", "공격력"), ("ignore", "방어율 무시 %")]
GEAR_INTRO = ("어센트에 적용되지 않는 장비(모자, 반지1~3)의 스탯을 입력하는 칸입니다. 스탯창 스펙에는 들어 있지만 어센트 데미지에는 빠지는 스탯이라, 어센트 계산에서 이만큼 뺍니다. "
              "장비 툴팁의 값을 그대로 옮겨 적고, 비워 두면 0입니다. 어센트를 쓰지 않으면(0회) 입력하지 않아도 됩니다. "
              "잠재옵션과 에디셔널 잠재옵션은 줄마다 옵션을 고르고 값을 적으며, 같은 옵션을 여러 줄에 고르면 더합니다. "
              "올스탯 %는 주스탯 %와 부스탯 %에 같은 값이 더해지고, 9레벨 당 +n은 스탯창 레벨을 9로 나눈 몫에 n을 곱합니다.")
# 잠재옵션 / 에디셔널 잠재옵션은 3줄이고, 줄마다 옵션 종류를 고르고 값을 적는다 (같은 옵션을 여러 줄에 고르면 더한다)
GEAR_POT = [("pot_main_pct", "주스탯 %"), ("pot_sub_pct", "부스탯 %"), ("pot_all_pct", "올스탯 %")]
GEAR_ADD = [("add_main", "주스탯"), ("add_main_pct", "주스탯 %"), ("add_sub", "부스탯"), ("add_sub_pct", "부스탯 %"),
            ("add_all", "올스탯"), ("add_all_pct", "올스탯 %"), ("add_attack", "공격력"), ("add_main_per9", "9레벨 당 주스탯 +"), ("add_sub_per9", "9레벨 당 부스탯 +")]
GEAR_LINES = 3
GEAR_KEYS = [k for k, _ in GEAR_BASE + GEAR_POT + GEAR_ADD]
GEAR_BASE_KEYS = [k for k, _ in GEAR_BASE]


def gear_default():
    d = {k: 0.0 for k in GEAR_BASE_KEYS}
    d["pot"] = [["", None] for _ in range(GEAR_LINES)]
    d["add"] = [["", None] for _ in range(GEAR_LINES)]
    return d

# 웹 사이트의 기본값 (Skills.py의 개인 값과 별개로 항상 이 값으로 시작한다)
WEB_DEFAULTS = {
    "SIM_TIME": 345, "t_0": 0, "t_n": 40,
    "ASCENT_USES": 0,
    **{g: gear_default() for g in GEAR_ITEMS},
    "LINK_LVL": {"데슬": 2, "데벤져": 2, "카데나": 2, "레테": 2, "키네시스": 2, "제논": 2,
                "아크": 2, "엔버": 2, "모도": 6, "모법": 6, "일리움": 2, "카인": 2},
}

OPTIONAL_INT = {"BIG_COUNT", "MINI_COUNT"}

# 화면에 보여 줄 이름 (나중에 바꾸려면 여기만 고치면 된다)
LABELS = {
    "base_spec": "스탯창 스펙", "abnormal_status_damage": "상태이상 추가 데미지", "UNION_LVL": "와헌 유니온 레벨",
    "SIM_TIME": "시뮬레이션 시간(초)", "t_0": "분석 구간 시작(초)", "t_n": "분석 구간 끝(초)",
    "ORIGIN_ON": "오리진 스킬 사용", "ORDER_ORIGIN_LAST": "후오리진 순서", "ORDER_ORIGIN_FIRST": "선오리진 순서", "ORIGIN_BIG_ORDER": "오리진을 사용할 극딜", "PILE_START_STACK": "릴파벙 시작 스택",
    "ORIGIN_MAX_WAIT": "오리진 최대 대기(초)", "ORIGIN_LATE_MODE": "오리진이 늦을 때", "ORDER_BIG": "극딜 순서", "ORDER_MINI": "준극딜 순서", "BUFF_ORDER": "극딜 버프 순서",
    "MF_LVL": "매그팡 레벨", "RPB_LVL": "릴리즈 파일 벙커 레벨", "HAMM_LVL": "해머 스매시 레벨", "CANNON_LVL": "리볼빙 캐논 레벨",
    "BUNK_BUST_LVL": "벙커 버스터 레벨", "BURN_BRK_LVL": "버닝 브레이커 레벨", "VULCAN_LVL": "발칸 펀치 레벨",
    "AFT_SHCK_LVL": "애프터이미지 쇼크 레벨", "INFANTRY_LVL": "인팬트리 레벨",
    "ORIGIN_LVL": "오리진 레벨", "OH_LVL": "오버히트 펀치 레벨", "HECATE_LVL": "솔 헤카테 레벨",
    "CONTI_LVL": "컨티뉴어스 링 레벨", "RESTRAINT_LVL": "리스트레인트 링 레벨",
    "SEED_CONTI": "컨티뉴어스 링 사용", "SEED_RESTRAINT": "리스트레인트 링 사용",
    "ORIGIN_P2_END": "오리진 후딜(초)", "ATTUNE_STYX": "스틱스를 감응시킬 스킬", "ATTUNE_PHLEG": "플레게톤을 감응시킬 스킬",
    "BUFF_DELAY": "버프 시퀀스 딜레이", "ASCENT_USES": "어센트 사용 횟수", "DOPING_ON": "도핑 / 액티브 버프 사용", "NOBLE_IGNORE": "노블 방어율 무시 %", "ASCENT_AFTER_DELAY": "어센트 후딜(초)", "BIG_COUNT": "극딜 사용 횟수", "MINI_COUNT": "준극딜 사용 횟수", "Hat": "모자 (어센트 미적용)", "Ring_1": "반지1 (어센트 미적용)", "Ring_2": "반지2 (어센트 미적용)", "Ring_3": "반지3 (어센트 미적용)",
    "SEED_RING_STAT": "반지4 (시드링 1개의 스탯, 고정)",
    "VANGUARD_LVL": "뱅가드 임팩트(어센트) 레벨", "LINK_ON": "링크 사용", "LINK_LVL": "링크 레벨",
}
# 화면에 보여 줄 설명. 여기에 없는 변수는 Skills.py의 주석을 그대로 보여 주고, ""로 적으면 설명을 보여 주지 않는다
NOTES = {
    "HAMM_LVL": "리볼빙 캐논 마스터리 레벨도 이 값을 따릅니다",
    "SEED_CONTI": "상시 적용되는 패시브 링입니다. 쓰지 않으면 스탯창 스펙에서 주스탯 4, 부스탯 4, 공격력 4를 뺍니다",
    "SEED_RESTRAINT": "버프 시퀀스에서 사용합니다 (재사용 대기시간 120초). 쓰지 않으면 스탯창 스펙에서 주스탯 4, 부스탯 4, 공격력 4를 뺍니다",
    "CONTI_LVL": "", "RESTRAINT_LVL": "",
    "PILE_START_STACK": "시작할 때 릴파벙 스택입니다. 5스택이면 첫 파일 벙커가 버스트 파일 벙커로 나갑니다",
    "ORIGIN_ON": "끄면 오리진을 한 번도 쓰지 않고, 극딜은 오리진 없이 진행합니다",
    "ORIGIN_BIG_ORDER": "몇 번째 극딜에서 오리진을 쓸지, 그리고 그때 오리진을 쓰는 방식(후오리진/선오리진)을 고릅니다",
    "BUFF_ORDER": "극딜 순서의 '버프' 단계에서 버프를 쓰는 순서입니다. 화살표로 순서를 바꾸세요. 꺼 둔 버프(링크 OFF, 시드링 OFF)는 건너뜁니다",
    "LINK_ON": "데슬, 데벤져, 레테, 키네시스, 제논은 효과가 스탯창 값에 이미 들어 있습니다. 끄면 그 레벨의 효과를 스탯창 값에서 빼고 계산합니다. 레벨을 올렸다면 스탯창 값도 같이 바꿔 주세요. 나머지 링크는 스탯창에 없어서 켜면 효과를 더합니다.",
    "LINK_LVL": "",
    "DOPING_ON": "스탯창 스펙(노도핑)에 더해지는 효과이며 어센트에는 적용되지 않습니다. 켜면 시뮬레이션 시작과 함께 쓰고, 지속시간이 끝나면 다시 쓰지 않습니다. 30분 도핑 아이템은 어센트에도 적용되니 스탯창 스펙에 포함해서 입력하세요. 노블(30분): 데미지, 보스 데미지, 크리티컬 데미지 +30%, 방어율 무시 / 영메(30분): 공격력 +4% / 세이람(15분): 공격력 +10%, 공격력 +50, 보스 데미지 +10%, 크리티컬 데미지 +16% / 콜렉터(8분): 공격력 +100, 올스탯 +30, 스킬 레벨 +2(공격력 +2, 릴파벙 직격과 충격파 기본 데미지 +3%p)",
    "NOBLE_IGNORE": "0~30%이고 2씩 오릅니다. 노블은 이 숫자와 같은 분만큼 지속됩니다 (2%면 2분, 30%면 30분, 0%면 효과 없음)",
    "BIG_COUNT": "시뮬레이션 시간 동안 쓸 극딜 횟수입니다 (t=0 첫 극딜 포함). 극딜과 준극딜은 번갈아 쓰고, 횟수를 다 쓴 쪽은 건너뜁니다. 모두 쓰고 나면 릴파벙, 오버히트, 매그팡 평딜만 합니다",
    "MINI_COUNT": "시뮬레이션 시간 동안 쓸 준극딜 횟수입니다. 0이면 준극딜을 쓰지 않습니다 (어센트는 준극딜 뒤에만 쓰므로 쓰지 않게 됩니다)",
    "ASCENT_AFTER_DELAY": "어센트 컷신(2.82초)이 끝난 뒤 다음 행동까지의 딜레이입니다",
    "ASCENT_USES": "준극딜 후 엔버링크가 끝난 뒤 ~ 다음 극딜 전에, 릴파벙 -> 오버히트를 쓰고 릴파벙이 쿨타임인 동안 매그팡 대신 씁니다. 릴파벙 쿨타임 1번에 1회씩, 시뮬레이션 시간과 상관없이 최대 이 횟수까지만 씁니다",
    "Hat": "", "Ring_1": "", "Ring_2": "", "Ring_3": "",
    "SEED_RING_STAT": "컨티뉴어스 링, 리스트레인트 링 모두 주스탯 +4, 부스탯 +4, 공격력 +4입니다. 어센트 계산에서는 사용 중인 시드링의 스탯만큼 자동으로 뺍니다. 시드링을 사용하지 않으면 스탯창 스펙에서도 그만큼 뺍니다 (둘 다 쓰지 않으면 주스탯 8, 부스탯 8, 공격력 8)",
    "ATTUNE_STYX": "스틱스가 같이 발동하는 스킬입니다. 재사용 대기시간이 있는 스킬만 고를 수 있습니다",
    "ATTUNE_PHLEG": "플레게톤이 같이 발동하는 스킬입니다. 솔 헤카테 레벨이 30 미만이면 사용할 수 없습니다",
}

# 스킬 레벨 화면의 소구역
SUBGROUPS = {
    "MF_LVL": "1~4차 스킬", "RPB_LVL": "1~4차 스킬", "HAMM_LVL": "1~4차 스킬", "CANNON_LVL": "1~4차 스킬",
    "BUNK_BUST_LVL": "5차 스킬", "BURN_BRK_LVL": "5차 스킬", "VULCAN_LVL": "5차 스킬", "AFT_SHCK_LVL": "5차 스킬", "INFANTRY_LVL": "5차 스킬",
    "ORIGIN_LVL": "6차 스킬", "OH_LVL": "6차 스킬", "HECATE_LVL": "6차 스킬", "VANGUARD_LVL": "6차 스킬",
}
SKILL_LEVELS = set(SUBGROUPS)          # 1~30 범위의 정수만 받는다
WEB_DEFAULTS.update({n: 30 for n in SKILL_LEVELS})      # 웹은 모든 스킬 레벨을 30(만렙)에서 시작한다
ATTUNE_LABELS = {"버닝 브레이커": "버닝 브레이커 (버브)", "소울 컨트랙트": "엔버 링크 (소울 컨트랙트)", "애프터이미지 쇼크": "애프터이미지 쇼크 (앺숔)", "벙커 버스터": "벙커 버스터 (벙버)"}

def set_sources(skills_src, attribute_src):
    _SRC["skills"] = skills_src
    _SRC["attribute"] = attribute_src
    _split.cache = None


def _split():
    """Skills.py를 (입력 영역, 엔진 영역)으로 나눈다. 마지막 '실행' 영역은 쓰지 않는다."""
    if getattr(_split, "cache", None):
        return _split.cache
    lines = _SRC["skills"].split("\n")
    stop = next(i for i, l in enumerate(lines) if _BANNER_STOP in l)
    tail = next(i for i, l in enumerate(lines) if _BANNER_TAIL in l)
    header = "\n".join(lines[: stop - 2])
    engine = "\n".join(lines[stop + 3: tail - 2])
    _split.cache = (header, engine)
    return _split.cache


# ---------------------------------------------------------------------------------------------
# 1. 입력 변수 읽기
# ---------------------------------------------------------------------------------------------
def _comments_by_line(src):
    out = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            out[tok.start[0]] = tok.string.lstrip("#").strip()
    return out


def _is_spec_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "CharaInfo"
            and not node.args and all(k.arg for k in node.keywords))


def _literal(node):
    try:
        return True, ast.literal_eval(node)
    except Exception:
        return False, None


def _kind_of(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, tuple):
        return "tuple"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return "other"


def parse_inputs():
    header, _ = _split()
    tree = ast.parse(header)
    comments = _comments_by_line(header)
    lines = header.split("\n")
    items = []
    order_vars = [n.targets[0].id for n in tree.body
                  if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id.startswith("ORDER_") and isinstance(n.value, ast.List)]
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if any(i["name"] == name for i in items):      # 같은 이름을 다시 대입하는 줄(base_spec = base_spec_no_link)은 입력이 아니다. 처음 대입만 쓴다
            continue
        # 설명: 같은 줄 끝 주석 + 바로 위의 주석 줄들
        note = []
        j = node.lineno - 1
        above = []
        while j >= 1 and lines[j - 1].strip().startswith("#") and "###" not in lines[j - 1]:
            above.append(lines[j - 1].strip().lstrip("#").strip())
            j -= 1
        note.extend(reversed(above))
        inline = [comments[l] for l in range(node.lineno, node.end_lineno + 1) if l in comments]
        note.extend(inline)
        item = {"name": name, "line": node.lineno, "comment": " / ".join(c for c in note if c)}
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "gear_stat" \
                and not node.value.args and all(k.arg in GEAR_KEYS and _literal(k.value)[0] for k in node.value.keywords):
            item["kind"] = "gear"                       # 장비 입력칸: 모든 항목을 보여 주고 안 적은 것은 0
            item["value"] = gear_default()
        elif _is_spec_call(node.value) and all(_literal(k.value)[0] for k in node.value.keywords):
            item["kind"] = "spec"
            item["value"] = {k.arg: ast.literal_eval(k.value) for k in node.value.keywords}
        else:
            ok, val = _literal(node.value)
            if ok and val is None and name in OPTIONAL_INT:
                item["kind"] = "optint"          # 숫자 또는 None(제한 없음)
                item["value"] = None
            elif ok and val is None and name.startswith("ATTUNE_"):
                item["kind"] = "str"
                item["value"] = None
            elif ok and _kind_of(val) != "other":
                item["kind"] = _kind_of(val)
                item["value"] = [list(x) if isinstance(x, tuple) else x for x in val] if isinstance(val, (list, tuple)) \
                    else ({str(k): v for k, v in val.items()} if isinstance(val, dict) else val)
                if isinstance(val, dict):
                    item["keytype"] = _kind_of(next(iter(val))) if val else "str"
                if isinstance(val, (list, tuple)) and val and isinstance(val[0], (list, tuple)):
                    item["kind"] = "other"
            elif isinstance(node.value, ast.Dict) and all(isinstance(v, ast.Name) for v in node.value.values) \
                    and all(_literal(k)[0] for k in node.value.keys):
                item["kind"] = "refmap"
                item["value"] = {str(ast.literal_eval(k)): v.id for k, v in zip(node.value.keys, node.value.values)}
                item["options"] = order_vars
            else:
                item["kind"] = "calc"
                item["value"] = ast.get_source_segment(header, node.value)
        if name == "SEED_RING_STAT":
            item["readonly"] = True                     # 고정값: 화면에서 바꿀 수 없다
        items.append(item)
    return items


# 화면에 묶어서 보여 줄 그룹. (제목, 이름 목록/접두사)
GROUPS = [
    ("스탯", ["base_spec", "abnormal_status_damage", "UNION_LVL", "PILE_START_STACK", "ASCENT_USES", "Hat", "Ring_1", "Ring_2", "Ring_3", "SEED_RING_STAT"]),
    ("시뮬레이션 시간", ["SIM_TIME", "t_0", "t_n"]),
    ("극딜 순서", ["ORIGIN_ON", "ORDER_ORIGIN_LAST", "ORDER_ORIGIN_FIRST", "ORIGIN_BIG_ORDER", "ORIGIN_MAX_WAIT",
                 "ORIGIN_LATE_MODE", "ORDER_BIG", "ORDER_MINI", "BIG_COUNT", "MINI_COUNT", "BUFF_ORDER"]),
    ("스킬 레벨", ["MF_LVL", "RPB_LVL", "HAMM_LVL", "CANNON_LVL", "BUNK_BUST_LVL", "BURN_BRK_LVL", "VULCAN_LVL",
               "AFT_SHCK_LVL", "INFANTRY_LVL", "ORIGIN_LVL", "OH_LVL", "HECATE_LVL", "VANGUARD_LVL"]),
    ("도핑", ["DOPING_ON", "NOBLE_IGNORE"]),
    ("시드링", ["SEED_CONTI", "CONTI_LVL", "SEED_RESTRAINT", "RESTRAINT_LVL"]),
    ("링크 스킬", ["LINK_ON", "LINK_LVL"]),
    ("스킬 딜레이", ["BUFF_DELAY", "MAG_FANG_DELAY", "HAMM_MAG_FANG_DELAY", "RELEASE_DELAY", "BURST_DELAY",
                 "OVERHEAT_DELAY", "ASCENT_AFTER_DELAY", "BREAKER_", "VULKAN_", "MINI_BUFF_DELAY", "BURST_START_DELAY"]),
    ("오리진", ["ORIGIN_P2_END"]),
    ("솔 헤카테", ["ATTUNE_STYX", "ATTUNE_PHLEG"]),
]


def _group_of(name):
    for title, keys in GROUPS:
        for k in keys:
            if name == k or (k.endswith("_") and name.startswith(k)):
                return title
    return "기타"


_ns_cache = {}


def _default_ns():
    if "ns" not in _ns_cache:
        _ns_cache["ns"] = build_namespace({})
    return _ns_cache["ns"]


ATTUNE_BUFF_EXCLUDE = ("리레",)      # 감응 목록에서 뺀 버프
ATTUNE_COMBO_EXCLUDE = ("스틱스", "플레게톤", "릴리즈 파일 벙커", "버스트 파일 벙커")      # 릴파벙/버파벙은 감응 목록에서 뺀다

def _choices():
    """Skills.py의 표에서 고를 수 있는 값의 목록을 읽어 온다 (코드가 바뀌면 목록도 같이 바뀐다)."""
    ns = _default_ns()
    out = {"ORIGIN_LATE_MODE": [{"value": v, "label": v} for v in ("단독", "미루기")]}
    attune = [{"value": None, "label": "감응시키지 않음"}]
    for v in ns.values():
        if isinstance(v, ns["Combo"]) and v.cooldown > 0 and v.name not in ATTUNE_COMBO_EXCLUDE:
            if v.name not in [a["value"] for a in attune]:
                attune.append({"value": v.name, "label": ATTUNE_LABELS.get(v.name, v.name)})
    for v in ns.values():                                  # 재사용 대기시간이 1분 이상인 버프(엔버 링크, 2분 쿨 버프 등)도 감응시킬 수 있다
        if isinstance(v, ns["BuffSkill"]) and v.cooldown_applies and v.cooldown >= 60 and v.name not in ATTUNE_BUFF_EXCLUDE:
            if v.name not in [a["value"] for a in attune]:
                attune.append({"value": v.name, "label": ATTUNE_LABELS.get(v.name, v.name)})
    out["ATTUNE_STYX"] = attune
    out["ATTUNE_PHLEG"] = attune
    out["UNION_LVL"] = [{"value": k, "label": f"{k}레벨 ({ns['UNION_TABLE'][k]}%)"} for k in sorted(ns["UNION_TABLE"])]
    out["PILE_START_STACK"] = [{"value": k, "label": f"{k}스택" + (" (버파벙으로 시작)" if k == 5 else "")} for k in range(6)]
    out["ASCENT_USES"] = [{"value": k, "label": f"{k}회" + (" (사용 안 함)" if k == 0 else "")} for k in range(4)]
    out["BIG_COUNT"] = [{"value": None, "label": "쿨마다 계속 사용"}] + [{"value": k, "label": f"{k}번"} for k in range(1, 13)]
    out["MINI_COUNT"] = [{"value": None, "label": "쿨마다 계속 사용"}] + [{"value": k, "label": f"{k}번"} for k in range(0, 13)]
    out["CONTI_LVL"] = [{"value": k, "label": str(k)} for k in sorted(ns["CONTI_TABLE"])]
    out["RESTRAINT_LVL"] = [{"value": k, "label": str(k)} for k in sorted(ns["RESTRAINT_TABLE"])]
    out["LINK_LVL"] = {n: [{"value": k, "label": str(k)} for k in sorted(t)] for n, t in ns["LINK_TABLES"].items()}
    return out


def _order(name):
    for _, keys in GROUPS:
        for i, k in enumerate(keys):
            if name == k:
                return i
            if k.endswith("_") and name.startswith(k):
                return i + 0.5
    return 999


def describe_inputs():
    items = parse_inputs()
    choices = _choices()
    for it in items:
        n = it["name"]
        it["group"] = _group_of(n)
        it["order"] = _order(n)
        it["hidden"] = n in HIDDEN or it["kind"] in ("calc", "other") or it["group"] == "기타"
        it["label"] = LABELS.get(n, "")
        if n in NOTES:
            it["note"] = NOTES[n]
        elif n in SKILL_LEVELS:
            it["note"] = ""
        if n in SUBGROUPS:
            it["sub"] = SUBGROUPS[n]
        if n in SKILL_LEVELS:
            it["min"], it["max"] = 1, 30
        if n == "SIM_TIME":
            it["min"], it["max"] = 1, 1200
        if _is_delay(n) and it["kind"] in ("int", "float"):
            it["kind"], it["min"] = "float", DELAY_MIN.get(n, 0)          # 소수 입력 가능 (BREAKER_PRE 등), 음수 불가
        if n == "NOBLE_IGNORE":
            it["min"], it["max"], it["step"] = 0, 30, 2
        if n in choices:
            it["choices"] = choices[n]
        if n in WEB_DEFAULTS:
            it["value"] = WEB_DEFAULTS[n]
    return json.dumps({"items": items, "groups": [g[0] for g in GROUPS],
                       "gear_intro": GEAR_INTRO, "gear": {"base": GEAR_BASE, "pot": GEAR_POT, "add": GEAR_ADD}}, ensure_ascii=False)


# ---------------------------------------------------------------------------------------------
# 2. 입력값을 코드에 덮어쓰기
# ---------------------------------------------------------------------------------------------
def _num(v, default):
    if isinstance(default, bool):
        return bool(v)
    if isinstance(default, int):
        return int(round(float(v)))
    if isinstance(default, float):
        return float(v)
    return v


def _to_source(item, value):
    k = item["kind"]
    d = item["value"]
    if k == "spec":
        parts = []
        for key, default in d.items():
            v = value.get(key, default)
            if v is None or v == "":                      # 비어 있는 칸(스탯 공백 모드)은 기본값으로 계산한다
                v = default
            parts.append("%s=%r" % (key, _num(v, default)))
        return "CharaInfo(%s)" % ", ".join(parts)
    if k == "optint":
        return "None" if value in (None, "") else repr(int(round(float(value))))
    if k == "gear":
        acc = {key: 0.0 for key in GEAR_BASE_KEYS}
        for key in GEAR_BASE_KEYS:
            v = value.get(key)
            acc[key] = 0.0 if v is None or v == "" else float(v)
        for key, v in list(value.get("pot") or []) + list(value.get("add") or []):
            if key in GEAR_KEYS and v not in (None, ""):
                acc[key] = acc.get(key, 0.0) + float(v)
        return "gear_stat(%s)" % ", ".join("%s=%r" % kv for kv in acc.items())
    if k in ("bool", "int", "float"):
        return repr(_num(value, d))
    if k == "str":
        return "None" if value is None else repr(str(value))
    if k in ("list", "tuple"):
        vals = list(value)
        if d and not isinstance(d[0], str):
            vals = [_num(v, d[0]) for v in vals]
        return repr(tuple(vals)) if k == "tuple" else repr(vals)
    if k == "dict":
        out = {}
        for key, default in d.items():
            kk = int(key) if item.get("keytype") == "int" else key
            out[kk] = _num(value.get(key, default), default)
        return repr(out)
    if k == "refmap":
        return "{%s}" % ", ".join("%s: %s" % (int(a) if str(a).lstrip("-").isdigit() else repr(a), b)
                                    for a, b in value.items())
    raise ValueError(item["name"])


# 딜레이(초)는 음수가 될 수 없다
DELAY_NAMES = ("BUFF_DELAY", "MAG_FANG_DELAY", "HAMM_MAG_FANG_DELAY", "RELEASE_DELAY", "BURST_DELAY",
               "OVERHEAT_DELAY", "ASCENT_AFTER_DELAY", "BREAKER_", "VULKAN_", "MINI_BUFF_DELAY", "BURST_START_DELAY", "ORIGIN_P2_END")


DELAY_MIN = {"MAG_FANG_DELAY": 0.01}        # 매그팡은 반복 행동이라 0초면 시간이 진행되지 않아 계산이 끝나지 않는다


def _is_delay(n):
    return n in DELAY_NAMES or (n.startswith(("BREAKER_", "VULKAN_")) and n not in ("BREAKER_GAP", "VULKAN_HITS", "BREAKER_HITS", "VULKAN_GAP", "VULKAN_HOLD", "BREAKER_INTERVAL"))


def patched_header(overrides):
    header, _ = _split()
    overrides = {k: (DELAY_MIN.get(k, 0) if _is_delay(k) and isinstance(v, (int, float)) and not isinstance(v, bool) and v < DELAY_MIN.get(k, 0) else v) for k, v in overrides.items()}
    items = {it["name"]: it for it in parse_inputs()}
    tree = ast.parse(header)
    lines = header.split("\n")
    edits = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n in overrides and n in items and items[n]["kind"] not in ("calc", "other"):
                edits.append((node.lineno, node.end_lineno, "%s = %s" % (n, _to_source(items[n], overrides[n]))))
    for a, b, text in sorted(edits, reverse=True):
        lines[a - 1:b] = [text]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------
# 3. 실행
# ---------------------------------------------------------------------------------------------
def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)

    def _missing(attr):
        raise AttributeError("%s.%s는 웹 버전에서 아직 지원하지 않습니다" % (name, attr))
    m.__getattr__ = _missing
    sys.modules[name] = m
    return m


def _prepare_modules():
    # 엔진은 numpy/pandas/matplotlib을 쓰지 않는다(분석 보조 함수만 pandas 사용). 웹에서는 불러오지 않는다
    for mod in ("numpy", "pandas", "matplotlib", "matplotlib.pyplot"):
        if mod not in sys.modules:
            _stub(mod)
    if "Attribute" in sys.modules and getattr(sys.modules["Attribute"], "_src", None) == _SRC["attribute"]:
        return
    m = types.ModuleType("Attribute")
    m._src = _SRC["attribute"]
    sys.modules["Attribute"] = m
    exec(compile(_SRC["attribute"], "Attribute.py", "exec"), m.__dict__)


def build_namespace(overrides):
    _prepare_modules()
    header, engine = _split()
    code = patched_header({**WEB_DEFAULTS, **overrides}) + "\n" + engine
    mod = types.ModuleType("skills_run")
    sys.modules["skills_run"] = mod       # dataclass가 모듈을 찾을 수 있게 등록
    exec(compile(code, "Skills.py", "exec"), mod.__dict__)
    return mod.__dict__


EXTRA_FIELDS = ("mainStat", "mainStatp", "fixedMainStat", "subStat", "subStatp", "fixedSubStat", "attack", "attackp", "damage",
                "bossDamage", "armorIgnore", "finalDamage", "critDamage", "attribResist", "buffDuration", "cooldown")


def extra_spec(ns, extra):
    """분석 탭의 '추가 스펙'을 CharaInfo로 만든다. 모두 0이면 None(입력 탭의 스탯은 바꾸지 않고 base_spec에 더하기만 한다)."""
    vals = {}
    for k, v in (extra or {}).items():
        if k in EXTRA_FIELDS and v not in (None, "", 0, 0.0):
            vals[k] = float(v)
    return ns["CharaInfo"](**vals) if vals else None


def simulate(overrides, extra=None):
    ns = build_namespace(overrides)
    spec = ns["base_spec"]
    ex = extra_spec(ns, extra)
    if ex is not None:
        spec = spec + ex                          # 예: 최종 데미지 10% 추가 -> base_spec + CharaInfo(finalDamage=10)
    state = ns["run_bunker_maxi"](spec=spec, duration=ns["SIM_TIME"], buff_delay=ns["BUFF_DELAY"],
                                  order=ns["ORDER_ORIGIN"], ascent_extra=ex)
    return ns, state


# ---------------------------------------------------------------------------------------------
# 4. 분석 (새 분석은 여기에 추가)
# ---------------------------------------------------------------------------------------------
# 점유율 목록에 같이 보여 줄 스킬 레벨 (입력 탭의 스킬 레벨 변수). 오라 웨폰, 플레게톤처럼 레벨 입력이 없는 스킬은 없다
LEVEL_VAR = {"벙커 버스터": "BUNK_BUST_LVL", "릴리즈 파일 벙커": "RPB_LVL", "버스트 파일 벙커": "RPB_LVL", "리볼빙 캐논": "CANNON_LVL",
             "리볼빙 캐논 마스터리": "MASTERY_LVL", "더블 팡": "MF_LVL", "매그넘 펀치": "MF_LVL", "발칸 펀치": "VULCAN_LVL",
             "버닝 브레이커": "BURN_BRK_LVL", "애프터이미지 쇼크": "AFT_SHCK_LVL", "인팬트리": "INFANTRY_LVL", "해머 스매시": "HAMM_LVL",
             "파이널 디스트로이어": "ORIGIN_LVL", "오버히트 펀치": "OH_LVL", "솔 헤카테": "HECATE_LVL", "스틱스": "HECATE_LVL",
             "뱅가드 임팩트": "VANGUARD_LVL"}


def analyze(ns, state):
    log = state.log                           # (t, 스킬, 데미지)
    sim_time = float(ns["SIM_TIME"])
    t0, tn = float(ns["t_0"]), float(ns["t_n"])
    total = sum(d for _, _, d in log)

    # 스킬별 합계
    by = {}
    for t, s, d in log:
        a = by.setdefault(s, [0, 0.0, 0.0])
        a[0] += 1
        a[1] += d
        a[2] = max(a[2], d)
    skills = [{"name": s, "count": c, "total": tot, "share": tot / total if total else 0, "max_hit": mx,
               "level": int(ns[LEVEL_VAR[s]]) if s in LEVEL_VAR and LEVEL_VAR[s] in ns else None}
              for s, (c, tot, mx) in by.items()]
    skills.sort(key=lambda r: -r["total"])

    # 누적 데미지(1초 간격)와 초당 데미지
    n = int(sim_time) + 1
    sec = [0.0] * n
    for t, s, d in log:
        sec[min(int(t), n - 1)] += d
    cum, run = [], 0.0
    for v in sec:
        run += v
        cum.append(run)

    # 구간(t_0~t_n) 안의 스킬별 초당 데미지 (스택 막대용)
    w0, w1 = int(t0), int(tn)
    win = {}
    for t, s, d in log:
        if w0 <= t < w1:
            win.setdefault(s, [0.0] * (w1 - w0))[int(t) - w0] += d

    # 행동 순서(콤보 시작 시각)
    rotation = []
    for item in getattr(state, "trace", []):
        try:
            rotation.append({"t": round(float(item[0]), 3), "name": getattr(item[1], "name", str(item[1]))})
        except Exception:
            pass

    ascent_times = [round(float(t), 2) for t, n in getattr(state, "trace", []) if n == "어센트"]
    return {
        "ascent_times": ascent_times, "ascent_uses": int(ns["ASCENT_USES"]),
        "total": total, "sim_time": sim_time, "window": [t0, tn],
        "per_second_total": total / sim_time if sim_time else 0,
        "skills": skills, "sec": sec, "cum": cum, "window_by_skill": win, "rotation": rotation,
    }


def recommend_times(overrides_json="{}", extra_json="{}"):
    """지금 입력(쿨감 등)으로 극딜/준극딜이 시작되는 시각(인팬트리를 누르는 시각)을 구한다. 시뮬레이션 시간을 정할 때 참고한다.
    시뮬레이션 시간은 극딜이 시작하기 직전(내림한 정수 초)으로 맞추면 마지막 극딜이 잘리지 않는다."""
    import math
    overrides = dict(json.loads(overrides_json or "{}"))
    overrides["SIM_TIME"] = 900
    overrides["BIG_COUNT"] = None
    overrides["MINI_COUNT"] = None
    ns, state = simulate(overrides, json.loads(extra_json or "{}"))
    tr = state.trace
    big, mini = [], []
    for i, (t, n) in enumerate(tr):
        if n == "극딜 시작 대기":
            nxt = tr[i + 1:i + 8]
            start = next((t2 for t2, n2 in nxt if n2 == "인팬트리"), t)       # 인팬트리를 누르는 시각이 극딜의 시작
            for t2, n2 in nxt:
                if n2.startswith("벙커 버스터"):
                    big.append(start); break
                if n2 == "소울 컨트랙트":
                    mini.append(start); break
    rows = [{"kind": "극딜", "n": k + 1, "start": round(t, 1), "sim": int(math.floor(t))} for k, t in enumerate(big[:5])]
    rows += [{"kind": "준극딜", "n": k + 1, "start": round(t, 1), "sim": int(math.floor(t))} for k, t in enumerate(mini[:5])]
    rows.sort(key=lambda r: r["start"])
    return json.dumps(rows, ensure_ascii=False)


def run_total(overrides_json="{}", extra_json="{}"):
    """총 데미지만 빠르게 구한다 (추가 스펙을 넣지 않은 값과 비교할 때 쓴다)."""
    ns, state = simulate(json.loads(overrides_json or "{}"), json.loads(extra_json or "{}"))
    return sum(d for _, _, d in state.log)


def run_sim(overrides_json="{}", extra_json="{}"):
    overrides = json.loads(overrides_json or "{}")
    ns, state = simulate(overrides, json.loads(extra_json or "{}"))
    return json.dumps(analyze(ns, state), ensure_ascii=False)
