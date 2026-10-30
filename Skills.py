from Attribute import CharaInfo
import math
import numpy as np
import heapq
import inspect
from dataclasses import dataclass, field, replace
import pandas as pd
import matplotlib.pyplot as plt
from typing import Callable, Any

# 도핑: base_spec은 도핑을 쓰지 않은 스탯창을 입력한다. 어센트에 적용되지 않는 도핑/액티브 버프 4종(노블, 영메, 세이람, 콜렉터)만 아래 DOPING_ON으로 켜서 더한다 (30분 도핑 아이템은 어센트에도 적용되므로 base_spec에 포함해서 입력)

# CharaInfo, 자버프 모두 사용 기준
# 링크 스킬: 데슬, 데벤져, 레테, 키네시스, 제논은 스탯창에 이미 반영된 값(내 캐릭터의 실제 링크 레벨 = LINK_LVL)이고,
#           카데나, 아크, 일리움, 엔버, 모도, 모법, 카인은 반영되어 있지 않다 -> 링크 스킬 효과표(버프 스킬 셀)에서 더한다
base_spec = CharaInfo(level=293, mainStat=6439, mainStatp=591, fixedMainStat=30900,
                      subStat=3256, subStatp=191, fixedSubStat=550,
                      attack=3293, attackp=138, damage=87, bossDamage=425,
                      armorIgnore=97.80, finalDamage=120.61, critDamage=98.3,
                      attribResist=5, cooldown=0, buffDuration=81)
abnormal_status_damage = CharaInfo(damage=8)        # 상추뎀(카데나 링크의 상추뎀은 제외: 카데나 ON/OFF와 레벨에 따라 링크 효과표에서 더한다)

# 와헌 유니온 20% 확률로 데미지 +20% (유니온 레벨에 따른 데미지 %)
UNION_LVL = 5                                  # 와헌 유니온 레벨 (4 또는 5)
UNION_TABLE = {4: 3.2, 5: 4}                   # 레벨 -> 데미지 %
union_effect = CharaInfo(damage=UNION_TABLE[UNION_LVL])



base_spec_no_link = base_spec + abnormal_status_damage + union_effect      # 링크 스킬(LINK_ON, LINK_LVL)을 더하기 전 스펙
base_spec = base_spec_no_link      # 링크 스킬이 더해진 최종 base_spec은 버프 스킬 셀의 '링크 스킬' 부분에서 만들어진다
# 시드링(컨티, 리레)과 메여축/리버티/엔버링크는 base_spec에 넣지 않고 버프 스킬로 따로 적용한다 (아래 '하이퍼 스킬 및 버프 스킬')
# 장비 스탯 입력: 장비 툴팁에서 옮겨 적는 값을 CharaInfo로 바꿔 준다 (어센트에 적용되지 않는 장비는 base_spec에서 이만큼 뺀다)
#  기본 스탯: main(주스탯), sub(부스탯), all_pct(올스탯 %: 주스탯 %와 부스탯 %에 같이 더해진다), attack(공격력), ignore(방어율 무시 %)
#  잠재옵션: pot_main_pct(주스탯 %), pot_sub_pct(부스탯 %), pot_all_pct(올스탯 %)
#  에디셔널 잠재옵션: add_main, add_main_pct, add_sub, add_sub_pct, add_all(올스탯), add_all_pct, add_attack,
#                    add_main_per9, add_sub_per9 (캐릭터 기준 9레벨 당 +n: base_spec.level를 9로 나눈 몫 x n)
def gear_stat(main=0, sub=0, all_pct=0, attack=0, ignore=0,
              pot_main_pct=0, pot_sub_pct=0, pot_all_pct=0,
              add_main=0, add_main_pct=0, add_sub=0, add_sub_pct=0, add_all=0, add_all_pct=0, add_attack=0,
              add_main_per9=0, add_sub_per9=0):
    per9 = int(base_spec.level) // 9
    return CharaInfo(mainStat=main + add_main + add_all + per9 * add_main_per9,
                     mainStatp=all_pct + pot_main_pct + pot_all_pct + add_main_pct + add_all_pct,
                     subStat=sub + add_sub + add_all + per9 * add_sub_per9,
                     subStatp=all_pct + pot_sub_pct + pot_all_pct + add_sub_pct + add_all_pct,
                     attack=attack + add_attack, armorIgnore=ignore)

# 어센트에 적용되지 않는 장비: 반지 1~3, 모자 (시드링 스탯에는 포함되지 않는다)
Ring_1 = gear_stat(main=104, sub=90, attack=75, pot_main_pct=27, pot_sub_pct=9)
Ring_2 = gear_stat(main=108, sub=108, attack=98, pot_main_pct=34)
Ring_3 = gear_stat(main=102, sub=102, attack=72, pot_main_pct=19, pot_sub_pct=12)
# 쿨감 제외
Hat = gear_stat(main=421, sub=213, attack=56, all_pct=5, pot_main_pct=34, pot_sub_pct=17)
# 시드링(컨티, 리레) 1개의 스탯. 반지 4칸에 2개를 끼므로 둘 다 쓰면 주스탯 8, 부스탯 8, 공격력 8이다.
# 사용하지 않는 시드링(SEED_CONTI/SEED_RESTRAINT가 False)은 base_spec에서 이 스탯만큼 빼고, 어센트 계산에서는 사용 중인 시드링만 뺀다
SEED_RING_STAT = CharaInfo(mainStat=4, subStat=4, attack=4)

# 오라웨폰
aw = CharaInfo(armorIgnore=16, finalDamage=6)

# 쓸샾
Sharp = CharaInfo(critDamage=8)

# 쓸컴뱃 + 숙련도 91 -> 90으로 감소
# 쓸컴뱃 메용, 소숫점 버림 / 기본 스탯: 5*level + 18 에서 1%p만큼 mainstat 감소(level은 base_spec의 레벨)
decrease_stat = math.floor((5*base_spec.level+18)*0.16) - math.floor((5*base_spec.level+18)*0.15)
Combat_ord1 = CharaInfo(mainStat=decrease_stat, 
                        attack=2, critDamage=1, bossDamage=1, finalDamage=2)


# 몬스터 속성 반감: 어센트는 몬스터의 속성 반감을 무시한다 -> ascent_spec의 속성 내성 무시를 100%로 한다 (코드에서 처리)
# 링크 스킬 전부 미적용: ascent_spec에서 링크 스킬 효과를 전부 뺀다 (코드에서 처리)
# 상추뎀, 와헌 유니온 미적용: ascent_spec에서 abnormal_status_damage, union_effect를 뺀다 (코드에서 처리)
# 쓸컴뱃을 쓰지 않으면 숙련도가 91% -> 90%로 줄어든다
ASCENT_PROFICIENCY = 0.90

# 어센트(뱅가드 임팩트) 데미지는 스탯창(base_spec)에서 아래 스탯을 뺀 스펙으로 계산한다 (링크 스킬, 상추뎀, 유니온은 코드가 알아서 뺀다)
ASCENT_EXCLUDE = Ring_1 + Ring_2 + Ring_3 + Hat + aw + Sharp + Combat_ord1      # + 사용 중인 시드링 스탯(코드에서 처리)
# 모자/반지 말고도 어센트에 적용되지 않는 효과가 base_spec에 들어 있으면 여기에 적는다 (예: 자버프 등 액티브 스킬 사용 효과, 조건부 패시브)
ASCENT_EXCLUDE_EXTRA = CharaInfo()


PILE = "파일 벙커"

# 시뮬레이션 시간, 단위: 초(sec) (최대 1200초)
SIM_TIME = 345
# 그래프를 그릴 때 볼 시간 구간(초). 시뮬레이션 자체에는 영향 없음
t_0 = 0
t_n = 40
WINDOW = (t_0, t_n)

# 순서 바꾸기 가능
ORDER_ORIGIN_LAST  = ["인팬트리", "버프", "버브", "발칸", "오리진"]     # 후오리진
ORDER_ORIGIN_FIRST = ["버프", "오리진", "인팬트리", "버브", "발칸"]     # 선오리진: 오리진 시전 시간만큼 발칸/인팬트리/버브 쿨타임 감소

# 오리진 스킬 사용 여부. False면 오리진을 전혀 쓰지 않는다 (극딜은 오리진 없이 ORDER_BIG 순서로 진행)
ORIGIN_ON = True

# 오리진을 쓰는 극딜(오리진극): {극딜 번호: 그 극딜의 행동 순서}. 극딜 번호는 t=0 첫 극딜이 1번.
# 오리진극마다 후오리진(ORDER_ORIGIN_LAST)/선오리진(ORDER_ORIGIN_FIRST)을 따로 고를 수 있다. 오리진은 1200초 동안 4번 쓴다.
# 예: 선오리진을 쓰려면 {1: ORDER_ORIGIN_FIRST, 4: ORDER_ORIGIN_FIRST, ...}
ORIGIN_BIG_ORDER = {1: ORDER_ORIGIN_LAST, 4: ORDER_ORIGIN_LAST, 7: ORDER_ORIGIN_LAST, 10: ORDER_ORIGIN_LAST}

# 오리진극에서 오리진 쿨이 아직 안 돌았을 때의 처리
#  ORIGIN_MAX_WAIT초 이하만 기다리면 되면: 극딜 시작을 늦춰서 오리진을 같이 쓴다 (쿨감 0~6초는 여기에 해당)
#  그보다 오래 기다려야 하면(ORIGIN_LATE_MODE): "단독" = 극딜은 제때 쓰고, 오리진은 쿨이 돌면 극딜과 따로 바로 쓴다 (쿨감 7초 이상: 12번째 극딜을 쓸 수 있음)
#                                            "미루기" = 오리진을 다음 극딜로 미룬다
ORIGIN_MAX_WAIT = 9        # 임시값: 쿨감 6초까지는 기다리고(대기 8초 이하), 7초부터는 따로 쓴다(대기 약 10초 이상)
ORIGIN_LATE_MODE = "단독"

ORDER_ORIGIN = ORIGIN_BIG_ORDER[min(ORIGIN_BIG_ORDER)]      # t=0 첫 극딜의 순서 (오리진극 중 가장 앞 번호)

# 재사용 규칙(극딜 사이클): 행동 이름 순서. "버프"는 모든 버프 시퀀스, "엔버"는 엔버링크 1개, 스틱스는 버브에 감응되어 같이 발동한다
ORDER_BIG  = ["인팬트리", "버프", "버브", "발칸"]      # 2분 극딜 (시작할 때 오리진이 곧 돌아 있으면 끝에 "오리진"을 붙여 오리진 극딜)
ORDER_MINI = ["인팬트리", "엔버", "버브"]               # 1분 준극딜

# 시뮬레이션 시간 동안 쓸 극딜/준극딜 횟수 (t=0 첫 극딜도 1번으로 센다). None이면 쿨이 돌 때마다 계속 쓴다
# 극딜과 준극딜은 번갈아 쓰고, 횟수를 다 쓴 쪽은 건너뛴다. 모두 쓴 뒤에는 평딜(릴파벙, 오버히트, 매그팡)만 한다
# 예: BIG_COUNT = 3, MINI_COUNT = 2 -> 극딜, 준극딜, 극딜, 준극딜, 극딜 (그 뒤는 평딜)
BIG_COUNT = None
MINI_COUNT = None

# 스킬 레벨
# 1~4차 스킬 레벨
MF_LVL = 29
RPB_LVL = 29
HAMM_LVL = 28
CANNON_LVL = 29
MASTERY_LVL = HAMM_LVL
# 5차 스킬 레벨
BUNK_BUST_LVL = 30
BURN_BRK_LVL = 10
VULCAN_LVL = 14
AFT_SHCK_LVL = 5
INFANTRY_LVL = 17
# 6차 스킬 레벨
ORIGIN_LVL = 9
OH_LVL = 9
HECATE_LVL = 9
VANGUARD_LVL = 9
# 시드링 레벨
CONTI_LVL = 4        # 컨티뉴어스 링
RESTRAINT_LVL = 4    # 리스트레인트 링


# 시작할 때 릴파벙 스택 (0~5). 5이면 시작 후 첫 파일 벙커가 버스트 파일 벙커(버파벙)
PILE_START_STACK = 0

# 스킬 딜레이
# 버프 시퀀스 딜레이, 버프당 100ms(0.1) / 블래는 총 8개 사용이지만, 1개는 딜과 관련이 없으므로 시뮬레이션에서는 7개만 구현
BUFF_DELAY = 0.8     
# 극딜 버프를 쓰는 순서: 벙버(벙커 버스터), 맥마(맥시마이즈 캐논), 앺숔(애프터이미지 쇼크), 메여축(메이플 여신의 축복), 리버티(윌 오브 리버티), 엔버(엔버링크), 리레(리스트레인트 링)
# 순서만 바꿔 쓴다 (7개를 모두 한 번씩 적어야 한다). 꺼 둔 버프(링크/시드링 OFF 등)는 건너뛴다
BUFF_ORDER = ["벙버", "맥마", "앺숔", "메여축", "리버티", "엔버", "리레"]

#매그팡
MAG_FANG_DELAY = 0.5
# 해매팡
HAMM_MAG_FANG_DELAY = 0.5
# 릴파벙
RELEASE_DELAY = 0.3
# 버파벙
BURST_DELAY = 0.3
# 오버히트
OVERHEAT_DELAY = 0.3
# 어센트: 컷신(ASCENT_DELAY)이 끝난 뒤 다음 행동까지의 딜레이
ASCENT_AFTER_DELAY = 0.2


# 버닝 브레이커: 키다운(선딜, 이 동안 데미지 없음) -> 키업 시 돌진 1회 + 폭발 6회 -> 후딜 없음
BREAKER_PRE = 1          # 선딜: 키다운 준비 시간 - 임시값
BREAKER_GAP = 0.01         # 돌진 -> 첫 폭발 간격 (0이면 키업과 동시)
BREAKER_INTERVAL = 0.0     # 폭발 간 간격 (0이면 6회가 동시에)
BREAKER_END_DELAY = 0.3    # 후딜 (인게임에서 없으나 다음 스킬을 누르는 사이의 딜레이 예측값)
BREAKER_HITS = 6           # 폭발 횟수

# 발칸 펀치: 1타 -> (gap) -> 2타 2초 동안 30회 -> (end_delay)
VULKAN_GAP = 0.01          # 1타 후 2타 시작까지의 딜레이(매우 짧음) - 임시값
VULKAN_HOLD = 2.0          # 2타 지속 시간
VULKAN_END_DELAY = 0.5     # 2타 종료 후 딜레이 - 임시값
VULKAN_HITS = 30           # 2타 발동 횟수






# 전투 시작: t=0은 전투 중이 아니라서 설치기/자동 공격(인팬트리, 헤카테)은 공격하지 않는다. 이 스킬의 키다운을 시작하면 전투가 시작된다
COMBAT_START = "버닝 브레이커"

# 인팬트리: 버프 시퀀스 전에 사용하는 설치형 공격. 선딜 후 INTERVAL 간격으로 HITS번 공격
# (이미 전투 중에 재사용하면 선딜 INFANTRY_PRE 후 첫 공격 / t=0처럼 전투 시작 전에 설치하면 COMBAT_START 키다운 시각에 첫 공격)
INFANTRY_PRE = 0.36        # 선딜: 사용 후 첫 공격까지 (인게임 360ms)
INFANTRY_DELAY = INFANTRY_PRE   # 다음 행동(버프 시퀀스)을 시작하기까지 걸리는 시간. 설치 후 바로 움직일 수 있으면 더 작게 - 임시값
INFANTRY_INTERVAL = 0.5    # 공격 간격
INFANTRY_HITS = 10         # 최대 공격 가능 횟수

# 쿨타임 감소(쿨감): 릴파벙/버파벙을 제외한 모든 스킬의 재사용 대기시간 x (1 - spec.cooldownp) - spec.cooldown(초). 릴파벙 계열은 PILE 쿨타임을 따로 관리한다
CDR_EXEMPT = ("릴리즈 파일 벙커", "버스트 파일 벙커")

# 불릿 장전: 맥마가 없을 때 불릿을 전부 소모하는 스킬(버브)을 쓰면, 소모한 시점(첫 타격)부터 BULLET_RELOAD초 동안 장전하느라 리볼빙 캐논이 발동하지 않는다
# (리캐 슬롯만 막히고 리캐마는 그대로 발동). 실린더 게이지는 불릿(리캐)을 써야 채워지므로 이때는 게이지도 차지 않는다.
# 매그팡(평딜)은 리캐 2번으로 불릿 2개를 쓰고 어드밴스드 차지 마스터리로 2개를 다시 장전하므로(매그팡 딜레이에 포함) 불릿이 줄지 않는다.
BULLET_RELOAD = 1.0                       # 불릿을 모두 소모한 뒤 장전 시간 - 임시값
BULLET_EMPTY_SKILLS = ("버닝 브레이커",)   # 불릿을 전부 소모하는 스킬

MINI_BUFF_DELAY = 0.1      # 준극딜에서 엔버링크 사용 후 다음 행동까지의 딜레이 - 임시값
BURST_START_DELAY = 0.30    # 극딜/준극딜 시작 전 딜레이: 평딜(매그팡)을 하다가 쿨이 돈 것을 보고 키보드에서 손을 떼 인팬트리를 누를 때까지 캐릭터가 멈춰 있는 시간 - 임시값
                            # (t=0의 첫 극딜은 제외. 극딜과 준극딜에 같은 값을 쓴다)

# 오라 웨폰: 자신의 공격 스킬을 쓸 때 쿨타임(5초)이 끝나 있으면 같이 발동
AURA_COOLDOWN = 5.25      # 인게임 전투분석(335초 62회)에 맞춘 값: 서버 지연 등으로 실제 쿨타임이 5초보다 조금 길다
AURA_EXCLUDE = ("인팬트리",)      # 이 스킬로는 오라 웨폰이 발동하지 않는다 (오버히트 펀치는 발동한다)

# 도핑 / 액티브 버프 ON/OFF (True면 사용). 어센트에는 적용되지 않는다. 시뮬레이션 시작(0초)에 쓰고 지속시간이 끝나면 다시 쓰지 않는다
#  노블(노블레스, 30분): 데미지 +30%, 보스 데미지 +30%, 크리티컬 데미지 +30%, 방어율 무시 +NOBLE_IGNORE% (0~30, 2씩 증가)
#  영메(영웅의 메아리, 30분): 공격력 +4%
#  세이람(15분 도핑): 공격력 +10%, 공격력 +50, 보스 데미지 +10%, 크리티컬 데미지 +16%
#  콜렉터(8분 도핑): 공격력 +100, 주스탯 +30, 부스탯 +30, 스킬 레벨 +2(공격력 +2, 릴파벙 직격/충격파 A, B, C 기본 데미지 +3%p)
DOPING_ON = {"노블": False, "영메": False, "세이람": False, "콜렉터": False}
NOBLE_IGNORE = 0       # 노블의 방어율 무시 % (0~30, 2의 배수: 0, 2, 4, ...)

# 시드링 ON/OFF (True면 사용). run_bunker_maxi(conti_on=..., restraint_on=...)로 그때그때 바꿀 수도 있다
SEED_CONTI = True        # 컨티뉴어스 링: 상시 적용 (이전 시뮬레이션은 base_spec에 컨티가 더해져 있어 ON과 같은 값이었다)
SEED_RESTRAINT = True   # 리스트레인트 링: 버프 시퀀스에서 사용(15초)

# 링크 스킬 ON/OFF와 레벨. 레벨별 효과는 버프 스킬 셀의 LINK_TABLES에 있다
# 게임에서 링크 레벨을 올렸으면 아래 LINK_LVL의 숫자만 바꾸면 된다 (바꾼 뒤 이 셀부터 아래로 다시 실행)
# 단, 데슬, 데벤져, 레테, 키네시스, 제논은 효과가 이미 스탯창(base_spec의 숫자)에 들어 있다.
#   이 5개의 LINK_LVL은 '스탯창에 반영된 레벨(내 캐릭터가 실제로 가진 레벨)'이고, OFF로 하면 그 레벨의 효과를 base_spec에서 뺀다.
#   레벨을 올렸다면 스탯창 값(위의 base_spec 숫자)도 같이 새로 옮겨 적고 LINK_LVL도 맞춰야 한다.
# run_bunker_maxi(link_on={"모도": False})처럼 ON/OFF만 그때그때 일부만 바꿀 수도 있다
LINK_ON  = {"데슬": True, "데벤져": True, "카데나": True, "레테": True, "키네시스": True, "제논": True,
            "아크": True, "엔버": True, "모도": True, "모법": True, "일리움": True, "카인": True}      

LINK_LVL = {"데슬": 2, "데벤져": 2, "카데나": 2, "레테": 2, "키네시스": 3, "제논": 2,
            "아크": 2, "엔버": 3, "모도": 6, "모법": 6, "일리움": 2, "카인": 2}

# 카인 링크: 보스에게 5번 공격 적중 = 사전 준비 1번, 사전 준비 5번이면 발동. 공격 적중 1번 = 공격 스킬 1회 발동(로그 1줄)로 센다
KAIN_HITS_PER_PREP = 5     # 사전 준비 1번에 필요한 공격 적중 횟수
KAIN_PREP_NEED = 5         # 발동에 필요한 사전 준비 횟수

# 오리진: 쿨 360초, 7.26초 동안 다른 행동 불가 + 0.5초 후딜(ORIGIN_P2_END)
#  0 ~ P1_LEN초: 첫타 P1_HITS회를 균등하게 -> GAP초 쉬고 -> P2_LEN초 동안 (첫타 P2_F회 + 후속타 P2_S회)를 균등하게
ORIGIN_P1_LEN = 3.0        # 첫 구간 길이
ORIGIN_P1_HITS = 23        # 첫 구간 첫타 횟수
ORIGIN_GAP = 2.0           # 두 구간 사이 쉬는 시간
ORIGIN_P2_END = 0.5        # 오리진 후딜 (스킬 가속으로 줄어드는 시간에는 포함되지 않음)
ORIGIN_P2_LEN = 2.26 + ORIGIN_P2_END # 두 번째 구간 길이 + 후딜
ORIGIN_P2_F = 20           # 두 번째 구간 첫타 횟수 (먼저 발동)
ORIGIN_P2_S = 30           # 두 번째 구간 후속타 횟수 (첫타가 끝나자마자 발동)
ORIGIN_DELAY = ORIGIN_P1_LEN + ORIGIN_GAP + ORIGIN_P2_LEN       # 7.76초 (다음 행동까지 걸리는 시간: 시전 7.26초 + 후딜 0.5초)
ORIGIN_ACCEL_REDUCTION = ORIGIN_DELAY - ORIGIN_P2_END           # 스킬 가속으로 줄어드는 쿨타임(초): 후딜을 뺀 오리진 시전 시간 7.26초
ORIGIN_ACCEL_DURATION = 15 # 스킬 가속 지속 시간
ORIGIN_ACCEL_CD_RANGE = (60, 120)    # 가속이 적용되는 스킬의 재사용 대기시간 범위

# 어센트(뱅가드 임팩트): 쿨타임 없이 보스 전투에서 3회만 쓸 수 있다. 다른 스킬과 상호작용하지 않는다
# (버프, 링크, 시드링, 추가타(리캐마/벙버/앺숔), 오라 웨폰, 카인/모도/일격필살 발동 없음)
# 딜 사이클: 준극딜을 쓰고 엔버링크가 끝난 뒤 ~ 다음 극딜 시작 전 사이에서만 쓴다. 릴파벙 -> 오버히트를 쓴 뒤 릴파벙이 쿨타임인 동안
# 매그팡 대신 어센트를 쓰고, 릴파벙 쿨타임 1번에 어센트는 1번만 쓴다 (ASCENT_USES회를 다 쓸 때까지, 시뮬레이션 시간과 무관)
ASCENT_USES = 3            # 어센트 사용 횟수 (0~3)
ASCENT_DELAY = 2.82        # 컷신 길이(초): 시전 중에는 무적이고 다른 행동을 할 수 없다
ASCENT_TICKS = 20          # 어센트 1회의 데미지(충격 14번 x 20회, 에너지의 잔재 12번 x 20회)가 컷신 2.82초에 걸쳐 균등하게 들어가는 횟수
# 솔 헤카테: 상시 공격(HECATE_INTERVAL초 간격). 스틱스/플레게톤 시전 시간 동안은 공격하지 못한다
HECATE_INTERVAL = 3.5      # 헤카테 공격 간격
HECATE_PARTICLES = 4       # 헤카테가 한 번 공격할 때 생성하는 솔 에르다 입자 수 (입자 1개 = 6타 공격 1회, 4개가 동시에 발동)
HECATE_FIRST = 0.0         # 전투 시작(COMBAT_START 키다운) 후 첫 공격까지 - 임시값
# 헤카테 공격 규칙: 마지막 공격에서 HECATE_INTERVAL초가 지나면 다음 공격. 그 시각이 스틱스/플레게톤 시전 구간 안이면 시전이 끝나자마자 공격하고,
# 거기서부터 다시 HECATE_INTERVAL초를 센다. 시전 구간이 아니면 계속 HECATE_INTERVAL초 주기로 공격한다.
# 스틱스/플레게톤은 감응 스킬: 감응시킨 스킬(쿨타임 있는 스킬)을 쓰는 시점에 같이 발동한다 (None이면 감응 안 함)
ATTUNE_STYX = "버닝 브레이커"         # 스틱스를 감응시킬 스킬 이름 (버브)
ATTUNE_PHLEG = "발칸 펀치"            # 플레게톤을 감응시킬 스킬 이름 (HECATE_LVL이 30 미만이면 사용 불가)
HECATE_AURA = False        # 헤카테 계열 공격(헤카테/스틱스/플레게톤)은 오라 웨폰을 발동시키지 않음
STYX_DELAY = 0.96          # 스틱스 시전 시간(이 동안 헤카테 공격 불가), 쿨 60초
STYX_HIT_AT = 0.0          # 스틱스 8타가 한 번에 들어가는 시각(사용 시작 기준) - 임시값
# 플레게톤: 쿨 120초, 시전 4.2초 (이 동안 헤카테 공격 불가)
PHLEG_DELAY = 4.2
PHLEG_T1 = 0.96            # 격류 1회 (4타)
PHLEG_T2 = (1.80, 2.88)    # 격류 PHLEG_T2_N회 (4타), 구간 안에서 균등 (양 끝 포함)
PHLEG_T2_N = 7
PHLEG_T3 = (3.48, 4.02)    # 만개 PHLEG_T3_N회 (6타), 구간 안에서 균등 (양 끝 포함)
PHLEG_T3_N = 10

###############################################################################################
###############################################################################################
###################################### 아래 코드 수정X #########################################
###############################################################################################
###############################################################################################


@dataclass(frozen=True, kw_only=True)
class Skill:
    name:str
    cooldown:float = 0  # sec 단위, 0이면 노쿨
    delay:float = 0     # 후딜(sec)

# 공격 스킬
@dataclass(frozen=True, kw_only=True)
class AttackSkill(Skill):
    base_pct:float
    pct_per_level:float = 0
    skill_level:int = 1
    hit_count:int
    # 매그팡 기준 해머 레벨
    hammer_base_pct:float = 0
    hammer_pct_per_level:float = 0
    hammer_level:int = 0
    # 스킬별 데미지 증가(하이퍼스킬), 코강 방무 등 CharaInfo delta로 저장
    bonus: CharaInfo = field(default_factory=CharaInfo)

    triggers: tuple["AttackSkill", ...] = ()    # triggers=(revolving_cannon),)
    tags: tuple[str, ...] = ()                   # tag=("bullet",)
    proc_group: str = ""                         # 앺숔 재발동 대기시간을 따로 세는 단위(비어 있으면 스킬 이름)

    @property
    def damage_pct(self):
        base = self.base_pct + self.pct_per_level*self.skill_level
        hamm = self.hammer_base_pct + self.hammer_pct_per_level*(self.hammer_level//3)
        total = base+hamm
        return total


# 연계
@dataclass(frozen=True, kw_only=True)
class Combo(Skill):
    parts: tuple[tuple[AttackSkill, int], ...]  # (스킬, 횟수), 순서대로
    # Skill.delay = 이 연계 1회 시간(i.e. 매그팡 500ms)
    offsets: tuple[float, ...] | None = None    # None이면 delay를 균등 분할, 지정하면 각 발동 시각(콤보 시작 기준)
    accel: "CooldownAccel | None" = None         # 이 연계를 쓰면 켜지는 스킬 가속(오리진)
    blocks_hecate: bool = False                  # True면 이 연계를 쓰는 동안(delay) 헤카테가 공격하지 못한다(스틱스, 플레게톤)
    starts_in_combat: bool = False               # True면 전투가 시작된 시각부터 offsets를 센다(인팬트리: 설치해도 전투 시작 전에는 공격하지 않음)

    @property
    def timeline(self):
        seq = [s for s, c in self.parts for _ in range(c)]  # (스킬, 횟수) -> 펼치기
        n = len(seq)
        if self.offsets is not None:
            assert len(self.offsets) == n, "offsets 길이는 펼친 발동 횟수와 같아야 함"
            return sorted(zip(self.offsets, seq), key=lambda x: x[0])      # 시각 순서로 정렬(같은 시각이면 입력 순서 유지)
        return [(i*self.delay /n, s) for i, s in enumerate(seq)]

# 스킬 가속(오리진): 사용 후 duration초 동안 재사용 대기시간이 cd_min~cd_max초인 스킬을 쓰면 그 스킬의 쿨타임이 reduction초 감소
@dataclass(frozen=True, kw_only=True)
class CooldownAccel:
    duration:float
    reduction:float
    cd_min:float
    cd_max:float


# 릴파벙
@dataclass
class SimState:
    t:float = 0.0
    next_ready:dict[str, float] = field(default_factory=dict)   # 쿨타임 그룹 -> 다시 쓸 수 있는 시각
    cannon_count:int = 0    # 실린더 게이지
    pile_count:int = 0      # 릴파벙 스택
    overheat_ready:bool = False   # 릴파벙 직후 수동 오버히트 1회 사용 가능 여부
    log:list = field(default_factory=list)  # (t, 스킬명, 데미지)
    trace:list = field(default_factory=list)    # i.e. (t, Combo) 로테이션 확인용
    skill_uses:dict = field(default_factory=dict)   # 스킬명 -> [남은 사용 횟수, 만료 시각] (해머 24회 등)
    accels:list = field(default_factory=list)        # 켜져 있는 스킬 가속: (만료 시각, CooldownAccel)
    events:list = field(default_factory=list)        # 예약된 이벤트 힙: (시각, 종류(0=버프 시전/1=공격), 순번, 대상)
    event_seq:int = 0
    passives:list = field(default_factory=list)      # 공격 스킬을 쓸 때 같이 발동하는 스킬(오라 웨폰)
    passive_next:dict = field(default_factory=dict)  # 스킬명 -> 다음에 발동할 수 있는 시각(쿨타임이 끝나는 시각)
    proc_state:dict = field(default_factory=dict)   # (버프명, 번호) -> {"last": 마지막 발동 시각, "left": 남은 발동 횟수}

    active_buffs:dict = field(default_factory=dict)     # 버프명 -> (버프, 만료 시각)
    cd_override:dict = field(default_factory=dict)      # 쿨타임 그룹 -> [대체 쿨타임, 남은 횟수, 만료 시각]
    hecate:Any = None                                   # 상시 공격하는 솔 헤카테 (없으면 None)
    hecate_interval:float = 3.5
    hecate_end:float = 0.0                              # 이 시각 이후로는 헤카테 공격을 예약하지 않는다
    hecate_blocks:list = field(default_factory=list)    # 헤카테가 공격할 수 없는 구간 (시작, 끝)
    attune:dict = field(default_factory=dict)           # 스킬명 -> 그 스킬을 쓸 때 같이 발동하는 헤카테 스킬들(감응)
    buff_duration:float = 0.0                           # 벞지(CharaInfo.buffDuration). run()이 spec에서 가져온다
    reload_until:float = 0.0                            # 이 시각 전까지는 불릿 장전 중(맥마가 없으면 리볼빙 캐논이 발동하지 않는다)
    cooldownp:float = 0.0                               # 쿨타임 감소 %(spec.cooldownp, 0.06 = 6%). run()이 spec에서 가져온다
    cooldown_sec:float = 0.0                            # 쿨타임 감소 n초(spec.cooldown). run()이 spec에서 가져온다
    ascent_spec:Any = None                              # 어센트 계산용 스펙(모자/반지/링크 등을 뺀 스펙). None이면 spec을 그대로 쓴다
    ascent_left:int = 0                                 # 남은 어센트 사용 횟수
    ascent_mark:float = -1.0                            # 마지막 어센트를 쓴 릴파벙 쿨타임(그 쿨타임이 끝나는 시각으로 구분)
    pile_t:float = -1.0                                 # 마지막으로 릴파벙을 쓴 시각
    mini_t:float = -1.0                                 # 마지막 준극딜 시작 시각
    next_burst:str = "mini"                              # 다음에 쓸 극딜 종류("big"=2분 극딜, "mini"=1분 준극딜). t=0 오프닝이 극딜이라 처음 값은 "mini"
    origin_alone:bool = False                            # 오리진을 극딜과 따로 쓰기로 정했고 아직 쓰지 않았다
    origin_idx:int = 0                                   # 지금까지 쓴 오리진 횟수 (t=0 오프닝에서 쓴 것 제외)
    mini_count:int = 0                                   # 지금까지 시작한 준극딜 횟수 (t=0 오프닝 제외)
    last_burst:str = "big"                               # 마지막으로 시작한 극딜의 종류("big" / "mini")
    big_count:int = 1                                    # 지금까지 시작한 극딜 횟수 (t=0 첫 극딜 포함, 다음 극딜의 번호 = big_count + 1)
    queue:list = field(default_factory=list)            # 극딜/준극딜의 남은 행동 대기열
    combat_started:bool = False                         # 전투가 시작되었는가
    combat_queue:list = field(default_factory=list)     # 전투 시작을 기다리는 공격: (오프셋, 스킬)
    link_triggers:list = field(default_factory=list)    # 저절로 켜지는 버프(TriggerBuff): 모도, 카인 링크
    trigger_hits:dict = field(default_factory=dict)     # 버프명 -> 지금까지 센 공격 적중 횟수


# 버프 중 특정 태그 스킬을 쓰면 추가로 발동하는 공격(애프터이미지 쇼크)
@dataclass(frozen=True, kw_only=True)
class Proc:
    skill:AttackSkill       # 발동하는 공격
    tag:str                 # 이 태그를 가진 스킬이 발동될 때 반응
    cooldown:float = 0.0    # 재발동 대기시간(초)
    limit:int | None = None # 버프 1회당 최대 발동 횟수(None이면 무제한)
    shared_cooldown:bool = False    # False: 재발동 대기시간을 발동시킨 스킬(proc_group)마다 따로 센다 / True: 모든 스킬이 하나를 공유


# 공격 스킬 연동 스킬: 자신의 공격 스킬(AttackSkill)이 발동될 때 쿨타임이 끝나 있으면 같이 발동 (오라 웨폰)
@dataclass(frozen=True, kw_only=True)
class Passive:
    skill:AttackSkill
    cooldown:float          # 재사용 대기시간(초): 발동한 시각부터 계산


# 버프 스킬
@dataclass(frozen=True, kw_only=True)
class BuffSkill(Skill):
    duration:float      # 지속 시간
    effect:CharaInfo = field(default_factory=CharaInfo)  # 버프 발동 시 추가되는 스펙 delta
    replaces:dict[str, AttackSkill] = field(default_factory=dict)   # 원본 스킬명 -> 대체 스킬(리캐 -> 벙버)

    tag_effects:dict[str, CharaInfo] = field(default_factory=dict)                  # 태그 스킬에만 적용
    pct_effects:dict[str, float] = field(default_factory=dict)                      # 태그 스킬의 기본 데미지 %p를 올린다(콜렉터의 스킬 레벨 +2)
    cooldown_override:dict[str, tuple[float, int]] = field(default_factory=dict)    # 쿨타임 그룹 -> (대체 쿨타임, 적용 횟수)
    extra_triggers:dict[str, tuple[AttackSkill, ...]] = field(default_factory=dict)   # 스킬명 -> 버프 중 추가로 발동하는 스킬(해머 -> 벙버)
    use_limits:dict[str, int] = field(default_factory=dict)                            # 스킬명 -> 버프 중 최대 사용 횟수(해머 24회)
    procs:tuple[Proc, ...] = ()                                                         # 버프 중 태그 스킬에 반응해 발동하는 공격
    buff_duration_applies:bool = False                                                  # True면 지속 시간이 buffDuration(벞지)만큼 늘어난다(엔버링크만 해당)
    cooldown_applies:bool = True                                                        # False면 재사용 대기시간 감소(쿨감)가 적용되지 않는다(모도, 카인 링크)
    

# 조건을 만족하면 저절로 켜지는 버프(모도 링크, 카인 링크)
# 재발동 대기시간이 끝나 있을 때 공격이 hits_needed번 적중하면 그 타격부터 켜진다 (대기시간은 켜진 시각부터 센다)
@dataclass(frozen=True, kw_only=True)
class TriggerBuff:
    buff:BuffSkill
    hits_needed:int = 1       # 1이면 대기시간이 끝난 뒤 첫 공격에서 바로 켜진다
    ignore:tuple = ()         # 이 이름의 공격으로는 켜지지 않고, 적중 횟수로도 세지 않는다

# 버프 시퀀스: 여러 버프를 한 번에 쓸 때 총 딜레이를 임의로 지정
@dataclass(frozen=True, kw_only=True)
class BuffCombo(Skill):
    buffs: tuple[BuffSkill, ...]     # 쓰는 순서대로
    # Skill.delay = 모든 버프를 한 번에 쓸 때의 총 딜레이

    @property
    def timeline(self):
        n = len(self.buffs)
        return [(i*self.delay/n, b) for i, b in enumerate(self.buffs)]   # 딜레이 안에서 균등 간격



@dataclass
class Rule:
    name:str
    when:Callable[[SimState], bool]         # 지금 이 행동을 할 수 있는가
    pick:Callable[[SimState], Any]          # 무엇을 쓸 것인가 (Combo 또는 BuffSkill)
    on_use:Callable[[SimState, Any], None] = lambda state, action: None     # 사용 직전 상태 갱신

# 스킬 레벨에 따라 붙는 bonus (6차 스킬의 10/20/30레벨 효과, 5차 스킬의 레벨별 최종뎀 등에도 그대로 쓸 수 있다)
_BONUS_STATS = [p for p in inspect.signature(CharaInfo.__init__).parameters if p not in ("self", "level", "bosslevel")]

def level_bonus(level, table, mode="replace"):
    """table: {필요 레벨: CharaInfo}. level 이상이 된 레벨의 효과를 합쳐서 bonus(CharaInfo)로 돌려준다.
    mode="replace": 같은 스탯이 여러 레벨에 있으면 가장 높은 레벨의 값 하나만 적용 (예: 10레벨 방무 20% -> 30레벨 방무 30%, 합이 아님)
    mode="add"    : 해당하는 레벨의 효과를 전부 더한다 (방무는 곱연산 합산)"""
    result = CharaInfo()
    for need in sorted(table):
        if level < need:
            continue
        if mode == "add":
            result = result + table[need]
        else:
            for k in _BONUS_STATS:
                v = getattr(table[need], k)
                if v:
                    setattr(result, k, v)
    return result


# 레벨에 따라 붙는 bonus: {필요 레벨: 효과}. 레벨만 바꾸면(origin_level) 자동으로 적용된다. (같은 스탯은 높은 레벨 값이 대체)
ORIGIN_BONUS_TABLE = {10: CharaInfo(armorIgnore=20),
                      20: CharaInfo(bossDamage=20),
                      30: CharaInfo(armorIgnore=50, bossDamage=50)}   # 표에는 '그 레벨에서의 합산 값'을 적는다 (30레벨 방무 50%)

# 5차 스킬 최종데미지 증가 단계
# 레벨당 1%씩 증가. 단, 1레벨일 때 11%, 10레벨일 때 25%, 20레벨일 때 40%, 30레벨일 때 60%.
# 기본 10 + 레벨, 그리고 10/20/30레벨 도달 시 각각 +5/+5/+10 추가 (1→11, 5→15, 10→25, 14→29, 20→40, 30→60)
FIFTH_FD_MILESTONES = {10: 5, 20: 5, 30: 10}
def fifth_fd(level):
    return 10 + level + sum(v for k, v in FIFTH_FD_MILESTONES.items() if level >= k)


# 솔 헤카테 레벨 보너스 (헤카테/스틱스/플레게톤 모두 HECATE_LVL 기준으로 받는다). 표에는 그 레벨에서의 합산 값
HECATE_BONUS_TABLE = {10: CharaInfo(armorIgnore=20, bossDamage=20),
                      20: CharaInfo(armorIgnore=40, bossDamage=40)}     # 30레벨은 플레게톤만 활성화(추가 수치 없음)

# 쓸컴뱃, 콜렉터 미반영

# =======================================================================================
# 건틀렛리볼버 직접 공격 스킬(+릴파벙) (리볼빙 캐논 마스터리, 애프터이미지쇼크 적용 스킬)
# (n)표기는 n이 적용됨을 의미, 별도 표기 없으면 둘 다 적용됨

# 매그넘 펀치
# 더블 팡
# 해머 스매시
# 허리케인 믹서(시뮬 내 미사용)
# 쇼크웨이브 펀치(시뮬 내 미사용)
# 릴리즈 파일 벙커(앺숔 1회)
# 버스트 파일 벙커(앺숔 3회)
# 발칸펀치(첫타 리캐마 1회+앺숔 1회 / 키다운 리캐마 2번씩, 앺숔은 쿨타임으로 키다운 동안 15회 -> 리캐마: 1 + 2*30 = 61, 앺숔: 1 + 15 = 16)
# 버닝 브레이커 돌진 데미지(리캐마 1회)
# 버닝 브레이커 폭발 데미지(앺숔 1회)
# 파이널 디스트로이어(오리진 스킬)(앺숔)

# 리볼빙 캐논
revolving_cannon = AttackSkill(name="리볼빙 캐논",
                               base_pct=236, pct_per_level=12, skill_level=CANNON_LVL, hit_count=4,
                               bonus=CharaInfo(finalDamage=120,armorIgnore=20),
                               tags=("bullets", "cylinder"))    # bullets: 불릿 사용(맥마 +35%) / cylinder: 실린더 게이지를 채움
# 1~4차 퍼뎀: 60 -> 100 -> 120 -> 매60+128, 팡100+103?
# 매그 -> 더블팡(리캐 업그레이드) -> 리캐 업그레이드2 -> 리캐 업그레이드3
# 6차 마코 1레벨 퍼뎀 = 232 +렙당10%
# 5차 코강 최종뎀+120%p, 방무+20%p
# 236 + 12*level로 업데이트 예정 10.22

# 리볼빙 캐논 마스터리
revolving_mastery = AttackSkill(name="리볼빙 캐논 마스터리",
                                base_pct=359, pct_per_level=11, skill_level=MASTERY_LVL, hit_count=1,
                                bonus=CharaInfo(finalDamage=120,armorIgnore=20))
# 5차 코강 최종뎀+120%p, 방무+20%p


# 블래스트 해머 스매시
blast_hammer = AttackSkill(name="해머 스매시",
                           base_pct=270, pct_per_level=3, skill_level=HAMM_LVL, hit_count=10+2,
                           bonus=CharaInfo(damage=10,armorIgnore=20)+CharaInfo(armorIgnore=20,finalDamage=120),
                           triggers=(revolving_mastery,),       # 해머는 리캐 미발동(벙버는 extra_triggers로 발동)
                           tags=("afterimage",))
# 1~4차 퍼뎀: 150 +130 +136
# 해머 + 허믹 = 416
# 하이퍼스킬 데미지+10%p, 방무+20%p
# 6차 마코 1레벨 퍼뎀 = 273 +렙당3%


# 매그넘 펀치
magnum_punch = AttackSkill(name="매그넘 펀치",
                           base_pct=575, pct_per_level=7, skill_level=MF_LVL, hit_count=3,
                           hammer_base_pct=15, hammer_pct_per_level=7, hammer_level=blast_hammer.skill_level,
                           bonus=CharaInfo(damage=10,armorIgnore=20)+CharaInfo(armorIgnore=20,finalDamage=120),
                           triggers=(revolving_cannon, revolving_mastery),
                           tags=("afterimage",))
# 1~4차 퍼뎀: 100 +100 +130 +186
# 매그 + 더킹 + 스웨이 + 플래시 무브 = 516
# 6차 마코 1레벨 퍼뎀 = 582 +렙당7% +(15 +해머3렙당7%)
# 하이퍼스킬 데미지+10%p, 방무+20%p
# 5차 코강 최종뎀+120%p, 방무+20%p


# 더블 팡
double_fang = AttackSkill(name="더블 팡",
                          base_pct=454, pct_per_level=6, skill_level=MF_LVL, hit_count=4,
                          hammer_base_pct=10, hammer_pct_per_level=6, hammer_level=blast_hammer.skill_level,
                          bonus=CharaInfo(damage=10,armorIgnore=20)+CharaInfo(armorIgnore=20,finalDamage=120),
                          triggers=(revolving_cannon, revolving_mastery),
                          tags=("afterimage",))
# 1~4차 퍼뎀: 150 +130 +136
# 팡 + 해머 + 쇼크 = 416
# 6차 마코 1레벨 퍼뎀 = 460 +렙당6% +(10 +해머3렙당6%)
# 하이퍼스킬 데미지+10%p, 방무+20%p
# 5차 코강 최종뎀+120%p, 방무+20%p



# 릴리즈 파일 벙커
shock_a = AttackSkill(name="릴리즈 파일 벙커", base_pct=430+228, pct_per_level=5, skill_level=RPB_LVL, hit_count=6,
                      bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=15), tags=("rpb_up",))
shock_b = AttackSkill(name="릴리즈 파일 벙커", base_pct=350+188, pct_per_level=6, skill_level=RPB_LVL, hit_count=6,
                      bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=15), tags=("rpb_up",))
shock_c = AttackSkill(name="릴리즈 파일 벙커", base_pct=360+158, pct_per_level=6, skill_level=RPB_LVL, hit_count=6,
                      bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=15), tags=("rpb_up",))
shock_d = AttackSkill(name="릴리즈 파일 벙커", base_pct=430, pct_per_level=10, skill_level=RPB_LVL, hit_count=6,
                      bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=15))
# 충격파 A, B, C는 4차 스킬의 리캐 업그레이드의 영향을 받는 중
# 

release_pile_bunker = AttackSkill(name="릴리즈 파일 벙커",
                                  base_pct=710+163, pct_per_level=15, skill_level=RPB_LVL, hit_count=8,
                                  bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=20)+CharaInfo(armorIgnore=80),
                                  triggers=(shock_a, shock_b, shock_c, shock_d),     # 충격파는 앺숔 미발동(직격만)
                                  tags=("afterimage", "rpb_up"))
burst_pile_bunker = AttackSkill(name="버스트 파일 벙커",
                                base_pct=490, pct_per_level=10, skill_level=RPB_LVL, hit_count=10,       # 10타짜리 폭발이 6번 발동(burst_action 참고)
                                bonus=CharaInfo(armorIgnore=20,finalDamage=120,damage=20)+CharaInfo(armorIgnore=80),
                                tags=("afterimage",))
# 직격 방무+80%
# 하이퍼스킬 직격 데미지+20%, 충격파 데미지+15%
# 5차 코강 최종뎀+120%p, 방무+20%p

# 맥시마이즈 캐논
maximize_cannon = BuffSkill(name="맥시마이즈 캐논",
                            duration=40, cooldown=120,
                            tag_effects={"bullets":CharaInfo(damage=35)},
                            cooldown_override={PILE:(0,13)},
                            use_limits={"해머 스매시":24})

# 메이플월드 여신의 축복: 최종뎀 +17% (60초, 쿨 120초)
goddess_glory = BuffSkill(name="메여축",
                          duration=60, cooldown=120,
                          effect=CharaInfo(finalDamage=17))

# 윌 오브 리버티: 데미지 +10% (60초, 쿨 120초)
liberty = BuffSkill(name="윌 오브 리버티",
                    duration=60, cooldown=120,
                    effect=CharaInfo(damage=10))

# 일격필살: 공격 시 4초 동안 데미지 +100%, 재발동 대기시간 30초 (쿨감, 벞지 미적용). 모도 링크처럼 공격이 적중하면 켜지는 버프라 아래 fatal_trigger로 발동시킨다
fatal_strike = BuffSkill(name="일격필살", duration=4, cooldown=30, cooldown_applies=False,
                         effect=CharaInfo(damage=100))

# 일격필살: 쿨이 끝난 뒤 첫 공격 적중에서 켜진다. 직접 시전한 공격에만 발동한다고 보고, 스틱스/헤카테/인팬트리/오라 웨폰은 발동시키지 못한다
# (t=0에서는 같은 시각에 인팬트리, 헤카테, 스틱스, 오라 웨폰이 먼저 나가지만 일격필살은 버브의 첫 타에 켜진다)
fatal_trigger = TriggerBuff(buff=fatal_strike, hits_needed=1, ignore=("스틱스", "솔 헤카테", "플레게톤", "인팬트리", "오라 웨폰"))

# ===== 링크 스킬 효과표 {링크: {레벨: 효과}} =====
# 레벨은 LINK_LVL, ON/OFF는 LINK_ON에서 바꾼다. 새 레벨의 수치는 이 표에만 추가하면 된다
LINK_TABLES = {
    # 스탯창에 이미 반영된 링크(base_spec에는 LINK_LVL 레벨 값이 들어 있다. OFF로 하면 그 효과를 뺀다)
    "데슬":     {2: CharaInfo(bossDamage=15),             3: CharaInfo(bossDamage=20)},
    "데벤져":   {2: CharaInfo(damage=10),                 3: CharaInfo(damage=15)},
    "레테":     {2: CharaInfo(damage=8),                  3: CharaInfo(damage=12)},
    "키네시스": {2: CharaInfo(critDamage=4),              3: CharaInfo(critDamage=6)},
    "제논":     {2: CharaInfo(mainStatp=10, subStatp=10), 3: CharaInfo(mainStatp=15, subStatp=15)},    # 올스탯 %
    # 스탯창에 반영되어 있지 않은 링크 중 항상 적용되는 효과
    "카데나":   {2: CharaInfo(damage=6+6),                3: CharaInfo(damage=9+9)},                    # 상추뎀 + 데미지 (몬스터에 상태이상이 항상 걸려 있다고 본다)
    "아크":     {2: CharaInfo(damage=11),                 3: CharaInfo(damage=16)},
    "일리움":   {2: CharaInfo(damage=10),                 3: CharaInfo(damage=15)},
    "모법":     {6: CharaInfo(damage=9,  armorIgnore=9),  7: CharaInfo(damage=12, armorIgnore=12),      # 약점 3중첩 기준 (중첩당 데미지, 방무)
                 8: CharaInfo(damage=12, armorIgnore=12), 9: CharaInfo(damage=15, armorIgnore=15)},
    # 버프로 켜지는 링크
    "엔버":     {2: CharaInfo(damage=45),                 3: CharaInfo(damage=60)},                     # 10초(벞지 적용), 쿨 60초
    "모도":     {6: CharaInfo(damage=18), 7: CharaInfo(damage=21), 8: CharaInfo(damage=24), 9: CharaInfo(damage=27)},   # 10초, 재발동 20초
    "카인":     {2: CharaInfo(damage=17),                 3: CharaInfo(damage=25)},                     # 20초, 재발동 40초
}
LINK_IN_SPEC = ("데슬", "데벤져", "레테", "키네시스", "제논")     # 스탯창에 이미 반영됨 (LINK_LVL 레벨 기준)
LINK_STATIC  = ("카데나", "아크", "일리움", "모법")                 # 전투 중 항상 켜져 있다고 보고 스펙에 더한다

def link_check():
    for name, lv in LINK_LVL.items():
        if lv not in LINK_TABLES[name]:
            raise ValueError(f"{name} 링크 {lv}레벨 효과가 LINK_TABLES에 없음 (있는 레벨: {sorted(LINK_TABLES[name])})")
link_check()

def link_effect(name, on):
    return LINK_TABLES[name][LINK_LVL[name]] if on[name] else CharaInfo()

# 엔버 링크(소울 컨트랙트): 데미지 +45%/+60%(2/3레벨) (기본 10초, 쿨 60초)
# 지속 시간만 buffDuration(벞지)만큼 늘어난다: buffDuration=81이면 10*1.81=18.1초 (다른 버프는 벞지의 영향을 받지 않는다)
soul_contract = BuffSkill(name="소울 컨트랙트",
                          duration=10, cooldown=60,
                          effect=LINK_TABLES["엔버"][LINK_LVL["엔버"]],
                          buff_duration_applies=True)


# 모도 링크(시프 커닝): 적에게 상태이상을 적용시키면 10초 동안 데미지 증가, 재발동 대기시간 20초 (쿨감, 벞지 미적용)
# 상태이상은 항상 걸려 있다고 보고, 첫 공격 적중(전투 시작)에 켜지고 재발동 대기시간이 끝난 뒤의 첫 공격 적중에서 다시 켜진다(공격 사이 간격만큼 조금씩 밀린다)
modo_buff = BuffSkill(name="모도 링크", duration=10, cooldown=20, cooldown_applies=False,
                      effect=LINK_TABLES["모도"][LINK_LVL["모도"]])
modo_trigger = TriggerBuff(buff=modo_buff, hits_needed=1)      # 스틱스(바인드, 상태이상)를 포함한 모든 공격이 켠다

# 카인 링크(프라이어 프리퍼레이션): 보스에게 5번 공격 적중 = 사전 준비 1번, 사전 준비 5번을 마치면 20초 동안 데미지 증가, 재발동 대기시간 40초 (쿨감, 벞지 미적용)
# 재발동 대기시간이 끝난 뒤부터 공격 적중을 센다
kain_buff = BuffSkill(name="카인 링크", duration=20, cooldown=40, cooldown_applies=False,
                      effect=LINK_TABLES["카인"][LINK_LVL["카인"]])
kain_trigger = TriggerBuff(buff=kain_buff, hits_needed=KAIN_HITS_PER_PREP*KAIN_PREP_NEED, ignore=("스틱스", "솔 헤카테", "인팬트리"))      # 스틱스, 헤카테, 인팬트리는 카인 링크를 못 켠다

# 시드링: 레벨별 효과표. 시드링 레벨을 바꾸려면 CONTI_LVL/RESTRAINT_LVL만 바꾸면 된다 (마력 증가는 블래스터에 해당 없어 넣지 않았다)
# 리스트레인트 링(액티브, 쿨 120초): 레벨별 공격력 증가와 지속 시간 (5레벨부터 지속 시간 20초)
RESTRAINT_TABLE    = {1: CharaInfo(attackp=17), 2: CharaInfo(attackp=34), 3: CharaInfo(attackp=51),
                      4: CharaInfo(attackp=68), 5: CharaInfo(attackp=68), 6: CharaInfo(attackp=85)}
RESTRAINT_DURATION = {1: 9, 2: 11, 3: 13, 4: 15, 5: 20, 6: 20}
# 컨티뉴어스 링(패시브): 레벨별 보스 데미지와 공격력 증가
CONTI_TABLE        = {1: CharaInfo(attackp=4,  bossDamage=9),  2: CharaInfo(attackp=6,  bossDamage=18), 3: CharaInfo(attackp=8,  bossDamage=27),
                      4: CharaInfo(attackp=10, bossDamage=36), 5: CharaInfo(attackp=12, bossDamage=45), 6: CharaInfo(attackp=14, bossDamage=54)}
for _name, _lv, _tb in (("컨티뉴어스 링", CONTI_LVL, CONTI_TABLE), ("리스트레인트 링", RESTRAINT_LVL, RESTRAINT_TABLE)):
    if _lv not in _tb:
        raise ValueError(f"{_name} {_lv}레벨 효과가 표에 없음 (있는 레벨: {sorted(_tb)})")

# 시드링 - 리스트레인트 링: 지속 시간은 레벨에 따라 다르다(4레벨 15초), 쿨 120초
restraint = BuffSkill(name="리레",
                      duration=RESTRAINT_DURATION[RESTRAINT_LVL], cooldown=120,
                      effect=RESTRAINT_TABLE[RESTRAINT_LVL])

# 시드링 - 컨티뉴어스 링: 상시 적용 (쿨타임 없음). run()의 always 인자로 시작 시각부터 켜 둔다
continuous = BuffSkill(name="컨티",
                       duration=math.inf,
                       effect=CONTI_TABLE[CONTI_LVL])

# 도핑 / 액티브 버프: 시뮬레이션 시작(0초)부터 지속시간 동안 켜진다 (재사용하지 않는다). 어센트는 버프를 받지 않으므로 적용되지 않는다
noble_buff = BuffSkill(name="노블", duration=1800, cooldown=0, cooldown_applies=False,
                       effect=CharaInfo(damage=30, bossDamage=30, critDamage=30, armorIgnore=NOBLE_IGNORE))
hero_echo_buff = BuffSkill(name="영메", duration=1800, cooldown=0, cooldown_applies=False,
                           effect=CharaInfo(attackp=4))
seiram_buff = BuffSkill(name="세이람", duration=900, cooldown=0, cooldown_applies=False,
                        effect=CharaInfo(attackp=10, attack=50, bossDamage=10, critDamage=16))
collector_buff = BuffSkill(name="콜렉터", duration=480, cooldown=0, cooldown_applies=False,
                           effect=CharaInfo(attack=100+2, mainStat=30, subStat=30),
                           pct_effects={"rpb_up": 3})
DOPING_BUFFS = {"노블": noble_buff, "영메": hero_echo_buff, "세이람": seiram_buff, "콜렉터": collector_buff}

# 링크 스킬 중 스펙에 더하는 부분: 스탯창에 반영된 링크는 OFF일 때만 LINK_LVL 레벨 효과를 빼고(ON이면 그대로), 반영되지 않은 링크는 ON일 때 효과를 더한다
# 엔버, 모도, 카인은 버프(엔버는 버프 시퀀스, 모도/카인은 TriggerBuff)로 따로 적용하므로 여기에 들어 있지 않다
def build_link_spec(spec_no_link, on=None):
    on = {**LINK_ON, **(on or {})}
    spec = spec_no_link
    for name in LINK_IN_SPEC:
        if not on[name]:
            spec = spec - LINK_TABLES[name][LINK_LVL[name]]
    for name in LINK_STATIC:
        spec = spec + link_effect(name, on)
    return spec

# 시드링을 사용하지 않으면 스탯창에 들어 있는 그 시드링의 스탯(주스탯 4, 부스탯 4, 공격력 4)을 뺀다
def seed_ring_total(conti_on, restraint_on):
    total = CharaInfo()
    for on in (conti_on, restraint_on):
        if on:
            total = total + SEED_RING_STAT
    return total

if not SEED_CONTI:
    base_spec_no_link = base_spec_no_link - SEED_RING_STAT
if not SEED_RESTRAINT:
    base_spec_no_link = base_spec_no_link - SEED_RING_STAT
base_spec = build_link_spec(base_spec_no_link)

# 30레벨 기준, 6차 강화 코어 반영
# 레벨 1 ~ 레벨 9   : 11~19% (1%씩 증가)
# 레벨10 ~ 레벨 19 : 25~34% (1%씩 증가)
# 레벨20 ~ 레벨 29 : 40~49% (1%씩 증가)
# 레벨30 : 60%
# 5개

# 벙커 버스터
bunker_buster_att = AttackSkill(name="벙커 버스터", 
                            base_pct=475, pct_per_level=0, skill_level=BUNK_BUST_LVL, hit_count=8,
                            bonus=CharaInfo(armorIgnore=100,finalDamage=fifth_fd(BUNK_BUST_LVL)),
                            tags=("bullets", "cylinder"))
# 벞지 미적용, 버프 예정 만렙기준 461 ->475%
bunker_buster_bff = BuffSkill(name="벙커 버스터",
                            duration=40, cooldown=120,
                            replaces={"리볼빙 캐논": bunker_buster_att},
                            extra_triggers={"해머 스매시": (bunker_buster_att,),
                                            "버닝 브레이커": (bunker_buster_att,),     # 돌진 1회 + 폭발 6회 = 7회
                                            "발칸 펀치": (bunker_buster_att,),         # 1타 1회 + 2타 30회 = 31회
                                            "파이널 디스트로이어": (bunker_buster_att,)})  # 오리진 사용 횟수만큼 73회
# 461 -> 475로 base_pct 업데이트 예정 10.22


# 발칸 펀치
vulkan_punch_s = AttackSkill(name="발칸 펀치",
                             base_pct=1485, pct_per_level=0, skill_level=VULCAN_LVL, hit_count=12,
                             bonus=CharaInfo(finalDamage=fifth_fd(VULCAN_LVL)),
                             triggers=(revolving_mastery, revolving_mastery),
                             tags=("afterimage",), proc_group="발칸 펀치 2타(키다운)")   # 리캐마가 2번씩 발동, 2초동안 30회, 총 공격횟수 12*30=360회
vulkan_punch_f = AttackSkill(name="발칸 펀치",
                             base_pct=1925, pct_per_level=0, skill_level=VULCAN_LVL, hit_count=15,
                             bonus=CharaInfo(finalDamage=fifth_fd(VULCAN_LVL)),
                             triggers=(revolving_mastery,),
                             tags=("afterimage",), proc_group="발칸 펀치 1타")
# 첫타 후 2초 키다운, 발칸펀치 사용횟수 1타:1회, 2타(2초 지속):30회, 총 1+30=31회, 공격횟수:15+12*30=375회


# 버닝 브레이커
burning_breaker_s = AttackSkill(name="버닝 브레이커",
                                base_pct=1925, pct_per_level=0, skill_level=BURN_BRK_LVL, hit_count=15,
                                bonus=CharaInfo(armorIgnore=100,finalDamage=fifth_fd(BURN_BRK_LVL)),
                                tags=("bullets", "afterimage"))    # 6번 발동(돌진 burning_breaker_f는 앺숔 미발동)
burning_breaker_f = AttackSkill(name="버닝 브레이커",
                                base_pct=1980, pct_per_level=0, skill_level=BURN_BRK_LVL, hit_count=15,
                                bonus=CharaInfo(armorIgnore=100,finalDamage=fifth_fd(BURN_BRK_LVL)),
                                triggers=(revolving_mastery,),
                                tags=("bullets",))


# 애프터이미지 쇼크: 버프 시퀀스(벙버, 맥마와 같이)로 사용, 액티브 효과만 구현(패시브 무시)
afterimage_shock_att = AttackSkill(name="애프터이미지 쇼크",
                                   base_pct=990, pct_per_level=0, skill_level=AFT_SHCK_LVL, hit_count=5,
                                   bonus=CharaInfo(finalDamage=fifth_fd(AFT_SHCK_LVL)))
afterimage_shock_bff = BuffSkill(name="애프터이미지 쇼크",
                                 duration=100, cooldown=120,
                                 procs=(Proc(skill=afterimage_shock_att, tag="afterimage", cooldown=0.1, limit=49),))   # shared_cooldown=False: 스킬(proc_group)마다 0.1초
# 지속 100초, 직접 공격 시 발동(재발동 0.1초), 버프 1회당 최대 49회


# 인팬트리
infantry = AttackSkill(name="인팬트리",
                       base_pct=961,pct_per_level=47,skill_level=INFANTRY_LVL,hit_count=12)
# 10번 공격(5초 걸림)-> 0.5에 1번 발동, 쿨 60초


# 오라 웨폰
aura_weapon = AttackSkill(name="오라 웨폰",
                          base_pct=1100, pct_per_level=0, skill_level=30, hit_count=6)
# 자신의 공격 스킬 사용 시 5초 쿨타임으로 발동(공격 타이밍이 쿨타임이 끝난 뒤여야 발동)
aura_passive = Passive(skill=aura_weapon, cooldown=AURA_COOLDOWN)   # 공격 스킬 사용 시 쿨 5초 / 최종뎀·방무 효과는 캐릭터 스펙에 이미 반영

# burning_breaker_f.bonus.finalDamage

# 4개

# 오리진 (파이널 디스트로이어)

origin_bonus = level_bonus(ORIGIN_LVL, ORIGIN_BONUS_TABLE)   # replace: 도달한 가장 높은 단계의 값 하나만 적용

# 첫타(열기): 10번 공격 x 43회 / 후속타(폭발): 14번 공격 x 30회 -> 사용 횟수 73회, 총 공격 횟수 850회
final_destroyer_f = AttackSkill(name="파이널 디스트로이어",
                                base_pct=750, pct_per_level=25, skill_level=ORIGIN_LVL, hit_count=10,
                                bonus=origin_bonus,
                                tags=("afterimage",), proc_group="오리진 첫타")
final_destroyer_s = AttackSkill(name="파이널 디스트로이어",
                                base_pct=770, pct_per_level=26, skill_level=ORIGIN_LVL, hit_count=14,
                                bonus=origin_bonus,
                                tags=("afterimage",), proc_group="오리진 후속타")
# 리볼빙 캐논 마스터리 미발동 / 벙커 버스터 73회 발동(벙버 buff의 extra_triggers) / 앺숔은 인게임에서 17+19, 18+18, 18+19, 19+19회
# 오리진 컷신 7260ms = 7.26초, 쿨타임 360초(키다운 시점부터)
# 오리진 사용 후 15초 동안 스킬 가속: 재사용 대기시간 60~120초인 스킬(발칸, 인팬트리, 버브)의 쿨타임이 오리진 시전 시간(7.26초)만큼 감소

# 어센트: 뱅가드 임팩트 (마스터 레벨 30)
# 충격: 14번 공격 x 20회(여기서는 1번에 14번 공격, ASCENT_TICKS번 반복), 829%(9레벨) + 레벨당 61%  /  에너지의 잔재: 12번 공격 x 20회, 1185%(9레벨) + 레벨당 88%  (10레벨: 890%, 1273%)
# 기본 효과 방무 60%, 보공 40%. 10/20/30레벨의 방무/보공 효과(+10/+10, +10/+10, +20/-)는 기본 효과에 합적용된다
# 표에는 그 레벨에서의 합산 값을 적는다 (10레벨: 방무 70 보공 50 / 20레벨: 방무 80 보공 60 / 30레벨: 방무 100 보공 60)
ASCENT_BONUS_TABLE = {1:  CharaInfo(armorIgnore=60,  bossDamage=40),
                      10: CharaInfo(armorIgnore=70,  bossDamage=50),
                      20: CharaInfo(armorIgnore=80,  bossDamage=60),
                      30: CharaInfo(armorIgnore=100, bossDamage=60)}
ascent_bonus = level_bonus(VANGUARD_LVL, ASCENT_BONUS_TABLE)
vanguard_impact_f = AttackSkill(name="뱅가드 임팩트",
                                base_pct=280, pct_per_level=61, skill_level=VANGUARD_LVL, hit_count=14,
                                bonus=ascent_bonus, tags=("ascent",))
vanguard_impact_s = AttackSkill(name="뱅가드 임팩트",
                                base_pct=393, pct_per_level=88, skill_level=VANGUARD_LVL, hit_count=12,
                                bonus=ascent_bonus, tags=("ascent",))
# 어센트 계산용 스펙: 링크 스킬 효과(스탯창에 반영된 5개 포함), 상추뎀, 와헌 유니온, ASCENT_EXCLUDE(모자/반지/오라웨폰/쓸샾/쓸컴뱃)와 사용 중인 시드링 스탯을 뺀다. 버프(액티브 스킬 사용 효과)도 받지 않는다(calc_damage)
ascent_spec = build_link_spec(base_spec_no_link, {n: False for n in LINK_ON}) - abnormal_status_damage - union_effect - ASCENT_EXCLUDE - seed_ring_total(SEED_CONTI, SEED_RESTRAINT) - ASCENT_EXCLUDE_EXTRA
ascent_spec = ascent_spec + CharaInfo(attribResist=100 - ascent_spec.attribResist)      # 어센트는 몬스터의 속성 반감을 무시한다(속성 내성 무시 100% -> 속성 보정 1.0)
# 컷신 길이 2820ms, 보스 전투에서 3회 사용 가능, 재사용 대기시간 없음
# 충격 14번 + 에너지의 잔재 12번이 ASCENT_TICKS번에 걸쳐 컷신(ASCENT_DELAY) 동안 균등하게 들어간다 (k번째 타이밍 = ASCENT_DELAY * k / ASCENT_TICKS)
ascent_action = Combo(name="어센트", delay=ASCENT_DELAY + ASCENT_AFTER_DELAY,
                      parts=((vanguard_impact_f, 1), (vanguard_impact_s, 1)) * ASCENT_TICKS,
                      offsets=tuple(ASCENT_DELAY * (k + 1) / ASCENT_TICKS for k in range(ASCENT_TICKS) for _ in range(2)))

#오버히트 펀치
overheat_punch = AttackSkill(name="오버히트 펀치",
                             base_pct=941, pct_per_level=39, skill_level=OH_LVL, hit_count=6,
                             triggers=(revolving_mastery,),
                             tags=("afterimage",))
overheat_punch_auto = AttackSkill(name="오버히트 펀치",
                             base_pct=568, pct_per_level=25, skill_level=OH_LVL, hit_count=2)
# 맥시마이즈 과열 시간 감소 효과 존재 동안 568 + 25*level 의 데미지를 2번 *3회 발동(자동사출)
# 자동 발동 오버히트는 afterimage 태그가 없다 -> 앺숔 미발동 (수동 overheat_punch만 발동)


# 헤카테
# 레벨 보너스(방무/보공): 헤카테/스틱스/플레게톤 모두 HECATE_LVL 기준
hecate_bonus = level_bonus(HECATE_LVL, HECATE_BONUS_TABLE)
hecate_phlegethon_s = AttackSkill(name="플레게톤",
                           base_pct=962, pct_per_level=0, skill_level=30, hit_count=6,
                           bonus=hecate_bonus, tags=("hecate",))     # 만개: 10번 발동
hecate_phlegethon_f = AttackSkill(name="플레게톤",
                         base_pct=1169, pct_per_level=0, skill_level=30, hit_count=4,
                         bonus=hecate_bonus, tags=("hecate",))       # 격류: 8번 발동 (발동 시각은 phleg_action의 offsets가 정한다)
# 0.96초 : 격류
# 1.80초 ~ 2.88초 : 격류 7회 발동
# 3.48초 ~ 4.02초 : 만개 10회 발동
# 플레게톤 30레벨 고정, 쿨타임 120초
# 플레게톤 사용하는 4.2초(4200ms) 동안 솔 헤카테는 공격 불가

# 플레게톤 쿨 120초
hecate_styx = AttackSkill(name="스틱스",
                   base_pct=100, pct_per_level=4, skill_level=HECATE_LVL, hit_count=8,
                   bonus=hecate_bonus, tags=("hecate",))
# 스틱스 쿨 60초, 발동 0.96초(960ms) 동안 솔 헤카테는 공격 불가
hecate = AttackSkill(name="솔 헤카테",
                     base_pct=214, pct_per_level=14, skill_level=HECATE_LVL, hit_count=6,
                     bonus=hecate_bonus, tags=("hecate",))      # 4번 발동
# 헤카테 공격 주기 3.5초(350ms)
# 10레벨:방무+20%,보공+20%, 20레벨:방무+20%,보공+20%, 30레벨:플레게톤 활성화
# 솔 헤카테가 스틱스를 사용하는 동안에는 0.96초, 플레게톤을 사용하는 동안에는 4.20초 동안 솔 에르다 입자를 생성할 수 없다. 

# 매그팡
mag_fang = Combo(name="매그팡", delay=MAG_FANG_DELAY,
                 parts=((magnum_punch, 1), (double_fang, 1)))

# 릴파벙, 버파벙
release_action = Combo(name="릴리즈 파일 벙커", delay=RELEASE_DELAY, cooldown=7,
                       parts=((release_pile_bunker,1),))
burst_action = Combo(name="버스트 파일 벙커", delay=BURST_DELAY, cooldown=7,
                       parts=((burst_pile_bunker,6),))      # 10타 폭발 x 6번, delay 안에서 균등 간격


# 해매팡
hamm_mag_fang = Combo(name="해매팡", delay=HAMM_MAG_FANG_DELAY,
                      parts=((blast_hammer, 1), (magnum_punch, 1),(double_fang, 1)))


# 벙버+오리진

# 오버히트
# 오버히트 펀치 (수동): 릴파벙 직후 1회, 일격 3회  -> delay는 임의로 조절
OVERHEAT_OFFSETS = (0.0, 0.05, 0.1)    # 일격 3회의 발동 시각 - 임시값 (앺숔 0.1초 재발동 때문에 간격이 중요)
overheat_action = Combo(name="오버히트 펀치", delay=OVERHEAT_DELAY,
                        parts=((overheat_punch, 3),), offsets=OVERHEAT_OFFSETS)

# 오버히트 자동 발동: 맥마 과열 시간 감소 효과가 적용되는 릴파벙/버파벙은 적중 시 강타(2타) x3회가 같이 나간다
# (자동 오버히트는 앺숔이 발동하지 않으므로, 릴파벙/버파벙의 triggers로 붙여 같은 시각에 발동시킨다)
auto_x3 = (overheat_punch_auto,) * 3
release_pile_bunker_oh = replace(release_pile_bunker, triggers=release_pile_bunker.triggers + auto_x3)
burst_pile_bunker_oh   = replace(burst_pile_bunker,   triggers=burst_pile_bunker.triggers + auto_x3)
release_action_oh = replace(release_action, parts=((release_pile_bunker_oh, 1),))
burst_action_oh   = replace(burst_action,   parts=((burst_pile_bunker_oh, 1), (burst_pile_bunker, 5)))   # 오버히트 자동은 첫 폭발에만


# 버닝 브레이커
def make_breaker_combo(pre=BREAKER_PRE, gap=BREAKER_GAP, interval=BREAKER_INTERVAL,
                       end_delay=BREAKER_END_DELAY, n=BREAKER_HITS):
    offsets = (pre,) + tuple(pre + gap + i*interval for i in range(n))    # 돌진: pre(키업), 폭발: 돌진 + gap부터 interval 간격
    return Combo(name="버닝 브레이커", cooldown=60, delay=pre + gap + (n-1)*interval + end_delay,
                 parts=((burning_breaker_f, 1), (burning_breaker_s, n)), offsets=offsets)

burning_breaker_action = make_breaker_combo()



# 발칸 펀치
def make_vulkan_combo(gap=VULKAN_GAP, hold=VULKAN_HOLD, end_delay=VULKAN_END_DELAY, n=VULKAN_HITS):
    offsets = (0.0,) + tuple(gap + i*hold/n for i in range(n))     # 1타: 0, 2타: gap부터 hold 동안 균등하게 n회
    return Combo(name="발칸 펀치", cooldown=120, delay=gap + hold + end_delay,
                 parts=((vulkan_punch_f, 1), (vulkan_punch_s, n)), offsets=offsets)

vulkan_action = make_vulkan_combo()


# 인팬트리: 선딜(INFANTRY_PRE) 후 0.5초 간격 10번. 설치형이라 공격이 나가는 동안 다음 행동(버프 시퀀스)을 한다. 전투 시작 전에 설치하면 첫 공격이 전투 시작 시각이 된다
def make_infantry_combo(pre=INFANTRY_PRE, delay=INFANTRY_DELAY, interval=INFANTRY_INTERVAL, n=INFANTRY_HITS):
    offsets = tuple(pre + i*interval for i in range(n))      # 첫 공격은 pre, 이후 interval 간격
    return Combo(name="인팬트리", cooldown=60, delay=delay,
                 parts=((infantry, n),), offsets=offsets, starts_in_combat=True)

infantry_action = make_infantry_combo()


# 오리진: 3초 동안 첫타 23회 -> 2초 쉼 -> 2.26초 동안 (첫타 20회 + 후속타 30회) 균등. 시전 중 다른 행동 불가
def make_origin_combo(p1_len=ORIGIN_P1_LEN, p1_hits=ORIGIN_P1_HITS, gap=ORIGIN_GAP,
                      p2_len=ORIGIN_P2_LEN, p2_f=ORIGIN_P2_F, p2_s=ORIGIN_P2_S):
    n2 = p2_f + p2_s
    off1 = [i*p1_len/p1_hits for i in range(p1_hits)]                       # 첫 구간: 0초부터 p1_len초까지 균등
    off2 = [p1_len + gap + j*p2_len/n2 for j in range(n2)]                  # 두 번째 구간: 쉰 뒤 p2_len초 동안 균등 (첫타 -> 후속타 순서)
    delay = p1_len + gap + p2_len
    accel = CooldownAccel(duration=ORIGIN_ACCEL_DURATION, reduction=delay - ORIGIN_P2_END,
                          cd_min=ORIGIN_ACCEL_CD_RANGE[0], cd_max=ORIGIN_ACCEL_CD_RANGE[1])
    return Combo(name="오리진", cooldown=360, delay=delay,
                 parts=((final_destroyer_f, p1_hits + p2_f), (final_destroyer_s, p2_s)),
                 offsets=tuple(off1 + off2), accel=accel)

origin_action = make_origin_combo()


# 스틱스: 시전 STYX_DELAY초 동안 헤카테 공격 불가, 8타는 STYX_HIT_AT에 한 번에
styx_action = Combo(name="스틱스", delay=STYX_DELAY, cooldown=60, parts=((hecate_styx, 1),),
                    offsets=(STYX_HIT_AT,), blocks_hecate=True)

# 플레게톤: 시전 4.2초 / 격류 1회(0.96) -> 격류 7회(1.80~2.88 균등) -> 만개 10회(3.48~4.02 균등)
def make_phleg_combo():
    off1 = [PHLEG_T1]
    off2 = [PHLEG_T2[0] + i*(PHLEG_T2[1]-PHLEG_T2[0])/(PHLEG_T2_N-1) for i in range(PHLEG_T2_N)]
    off3 = [PHLEG_T3[0] + j*(PHLEG_T3[1]-PHLEG_T3[0])/(PHLEG_T3_N-1) for j in range(PHLEG_T3_N)]
    return Combo(name="플레게톤", delay=PHLEG_DELAY, cooldown=120,
                 parts=((hecate_phlegethon_f, 1 + PHLEG_T2_N), (hecate_phlegethon_s, PHLEG_T3_N)),
                 offsets=tuple(off1 + off2 + off3), blocks_hecate=True)

phleg_action = make_phleg_combo()

# 데미지 계산 함수
def calc_damage(spec, skill, t=0.0, state=None):
    if "ascent" in skill.tags:                        # 어센트: 버프(액티브 스킬 사용 효과)를 받지 않고, 모자/반지/링크를 뺀 스펙으로 계산
        base = state.ascent_spec if state is not None and state.ascent_spec is not None else spec
        s = base + skill.bonus
        s.proficiency = (1 + ASCENT_PROFICIENCY) / 2      # 쓸컴뱃을 빼면 숙련도 90%
        return s.get_DPL() * skill.damage_pct * 0.01 * skill.hit_count
    s = spec + skill.bonus
    pct = skill.damage_pct
    if state is not None:
        for buff, expire in state.active_buffs.values():
            if expire > t:                              # 발동 시각 기준 만료 판정
                s = s + buff.effect
                for tag in skill.tags:
                    if tag in buff.tag_effects:
                        s = s + buff.tag_effects[tag]
                    pct += buff.pct_effects.get(tag, 0)
    return s.get_DPL() * pct *0.01 * skill.hit_count

# 버프 등록: 시각 t에 켜진다(시간 진행은 execute가 담당)
def cast(buff, state, t):
    dur = buff.duration * (1 + 0.01*state.buff_duration) if buff.buff_duration_applies else buff.duration    # 엔버링크만 벞지 적용
    state.active_buffs[buff.name] = (buff, t + dur)
    state.next_ready[buff.name] = t + (max(0.0, buff.cooldown * (1 - state.cooldownp) - state.cooldown_sec) if buff.cooldown_applies else buff.cooldown)     # 쿨감 %를 먼저, 그 다음 n초 감소 (모도/카인/일필은 미적용)
    for group, (value, uses) in buff.cooldown_override.items():
        state.cd_override[group] = [value, uses, t + dur]
    for skill_name, limit in buff.use_limits.items():
        state.skill_uses[skill_name] = [limit, t + dur]
    for i, p in enumerate(buff.procs):                  # 재사용하면 발동 횟수/대기시간 초기화
        state.proc_state[(buff.name, i)] = {"last": {}, "left": p.limit}
    for h in state.attune.get(buff.name, ()):           # 버프(엔버 링크 등)에 감응시킨 헤카테 스킬도 버프가 켜지는 시점에 같이 발동한다
        attune_cast(h, state, t)

def pile_cooldown(base, state):
    ov = state.cd_override.get(PILE)
    if ov and ov[1] > 0 and state.t < ov[2]:         # 남은 횟수가 있고 버프가 살아 있을 때만
        ov[1] -= 1
        return ov[0]
    return base


# 리캐,벙버 발동 / 활성 버프의 replaces에 이름이 있으면 대체 스킬을 돌려준다
def resolve(skill, t, state):
    for buff, expire in state.active_buffs.values():
        if expire > t and skill.name in buff.replaces:      # 시전 시각 t 기준으로 만료 판단
            return buff.replaces[skill.name]
    return skill

# 버프가 추가로 발동시키는 스킬(해머에는 리캐가 안 나가지만 벙버는 나간다)
def extra_triggers(skill, t, state):
    out = []
    for buff, expire in state.active_buffs.values():
        if expire > t:
            out.extend(buff.extra_triggers.get(skill.name, ()))
    return out


# 활성 버프 중 이 스킬(태그)에 반응해 발동하는 공격 목록 - 재발동 대기시간/횟수 제한을 여기서 처리
def procs_for(skill, t, state):
    out = []
    for buff, expire in state.active_buffs.values():
        if expire <= t:
            continue
        for i, p in enumerate(buff.procs):
            if p.tag not in skill.tags:
                continue
            st = state.proc_state[(buff.name, i)]
            if st["left"] is not None and st["left"] <= 0:
                continue
            key = "*" if p.shared_cooldown else (skill.proc_group or skill.name)    # 재발동 대기시간을 세는 단위
            if t - st["last"].get(key, -1e9) < p.cooldown - 1e-9:      # 재발동 대기시간 중
                continue
            st["last"][key] = t
            if st["left"] is not None:
                st["left"] -= 1
            out.append(p.skill)
    return out


# 맥마가 켜져 있는가 / 불릿 장전 중인가(맥마가 없을 때만 해당)
def maximize_active(state, t):
    b = state.active_buffs.get(maximize_cannon.name)
    return b is not None and b[1] > t

def bullets_blocked(state, t):
    return t < state.reload_until and not maximize_active(state, t)

# 저절로 켜지는 버프(모도, 카인 링크): 이 타격에서 조건이 채워지면 이 타격부터 버프가 적용된다
# 재발동 대기시간 중에는 공격 적중을 세지 않는다
def check_link_triggers(state, t, skill):
    for tb in state.link_triggers:
        if skill.name in tb.ignore:                      # 이 버프를 켜지 못하는 공격(예: 스틱스는 카인 링크, 일격필살을 못 켠다)
            continue
        name = tb.buff.name
        ready = state.next_ready.get(name)               # None이면 아직 한 번도 켜지지 않았다
        if ready is not None and t < ready - 1e-9:
            continue
        n = state.trigger_hits.get(name, 0) + 1
        if n < tb.hits_needed:
            state.trigger_hits[name] = n
            continue
        state.trigger_hits[name] = 0
        cast(tb.buff, state, t)

# 스킬 사용 + 추가타(리캐, 리캐마, 벙버 등) 발동
def fire(skill, t, state, spec):
    original = skill                                 # 대체되기 전 스킬(트리거 슬롯)
    if original.name == revolving_cannon.name and bullets_blocked(state, t):
        return                                       # 불릿 장전 중에는 리캐 슬롯이 발동하지 않는다(벙버로 대체되는 것도 포함)
    if "ascent" in skill.tags:                       # 어센트는 다른 스킬과 상호작용하지 않는다: 추가타/오라 웨폰/링크 발동 없이 데미지만 기록
        state.log.append((t, skill.name, calc_damage(spec, skill, t, state)))
        return
    check_link_triggers(state, t, skill)             # 모도/카인 링크, 일격필살: 이 타격으로 조건이 채워지면 이 타격부터 적용
    skill = resolve(skill, t, state)                 # 벙버 활성 중이면 리캐 -> 벙버
    state.log.append((t, skill.name, calc_damage(spec, skill, t, state)))

    lim = state.skill_uses.get(original.name)        # 사용 횟수 제한(해머 24회)
    if lim and t < lim[1]:
        lim[0] -= 1

    # 공격 스킬 연동(오라 웨폰): 쿨타임이 끝나 있으면 같이 발동하고, 발동한 시각부터 쿨타임이 시작된다
    for p in ([] if (('hecate' in skill.tags and not HECATE_AURA) or skill.name in AURA_EXCLUDE) else state.passives):
        if skill.name != p.skill.name and t >= state.passive_next.get(p.skill.name, 0.0) - 1e-9:
            state.passive_next[p.skill.name] = t + p.cooldown
            fire(p.skill, t, state, spec)

    # 실린더 게이지: 리캐/벙버처럼 게이지를 채우는 스킬(cylinder 태그)이 발동될 때 쌓인다
    if "cylinder" in skill.tags and t >= state.next_ready.get(PILE, 0):
        state.cannon_count = min(6, state.cannon_count + 1)   # 쿨타임 중에는 실린더 안참
        
    for trig in skill.triggers:
        fire(trig, t, state, spec)                   # 같은 시각, 재귀
    for extra in extra_triggers(original, t, state):
        fire(extra, t, state, spec)                  # 버프가 추가로 발동시키는 스킬
    for p in procs_for(skill, t, state):
        fire(p, t, state, spec)                      # 태그에 반응하는 버프 공격(앺숔)


# ===== 이벤트 예약 =====
# 행동의 타격/버프 시전은 바로 실행하지 않고 시각을 붙여 예약해 둔다.
# 시간이 흐르면(flush) 시각 순서대로 실행하므로 행동이 끝난 뒤에 나가는 공격(인팬트리)도 정확한 시각의 버프를 받고,
# 오라 웨폰의 쿨타임도 실제 공격 시각 순서대로 계산된다.
def schedule(state, t, kind, obj):
    heapq.heappush(state.events, (t, kind, state.event_seq, obj))     # kind 0: 버프 시전 / 1: 공격 / 2: 헤카테 상시 공격 (같은 시각이면 시전이 먼저)
    state.event_seq += 1

# 솔 헤카테 상시 공격: 이벤트(kind 2)로 예약. 스틱스/플레게톤 시전 구간이면 공격하지 못한다
def hecate_tick(state, t, spec):
    blk = next(((s, e) for s, e in state.hecate_blocks if s - 1e-9 <= t < e - 1e-9), None)
    if blk:
        nxt = blk[1]                                     # 시전 구간에 걸렸으면 시전이 끝나자마자 공격(공격 후 다시 간격을 센다)
    else:
        for _ in range(HECATE_PARTICLES):                # 입자 수만큼 같은 시각에 발동 (6타 공격 x 4회)
            fire(state.hecate, t, state, spec)
        nxt = t + state.hecate_interval
    if nxt <= state.hecate_end + 1e-9:
        schedule(state, nxt, 2, None)

# 감응: 감응시킨 스킬을 쓰는 시점(키다운)에 헤카테 스킬(스틱스/플레게톤)이 같이 발동한다. 쿨타임 중이면 발동하지 않는다.
# 발동하는 동안 헤카테는 공격하지 못하지만, 본체의 행동 시간(delay)에는 영향이 없다.
def attune_cast(h, state, t=None):
    t = state.t if t is None else t                      # 버프에 감응시킨 경우 버프가 켜지는 시각을 넘겨 받는다
    if t < state.next_ready.get(h.name, 0.0) - 1e-9:
        return
    state.next_ready[h.name] = t + cooldown_with_accel(h.cooldown, t, state, h.name)
    state.hecate_blocks.append((t, t + h.delay))
    for off, s in h.timeline:
        schedule(state, t + off, 1, s)

def flush(state, upto, spec):
    # upto 시각까지(포함) 예약된 이벤트를 시각 순서대로 실행. upto=inf이면 남은 이벤트를 모두 실행
    eps = 1e-9
    while state.events and state.events[0][0] <= upto + eps:
        t, kind, _, obj = heapq.heappop(state.events)
        if kind == 0:
            cast(obj, state, t)
        elif kind == 2:
            hecate_tick(state, t, spec)
        else:
            fire(obj, t, state, spec)


# 스킬 가속(오리진) 반영 쿨타임: 스킬 사용 시각 t에 가속이 켜져 있고 쿨타임이 범위 안이면 reduction만큼 감소
def cooldown_with_accel(cd, t, state, name=""):
    base = cd
    if name not in CDR_EXEMPT:
        cd = max(0.0, cd * (1 - state.cooldownp) - state.cooldown_sec)    # 쿨감 %를 먼저 적용하고 그 다음 쿨감 n초(CharaInfo.cooldown)를 뺀다 (릴파벙/버파벙 제외)
    for expire, acc in state.accels:
        if t < expire and acc.cd_min <= base <= acc.cd_max:
            cd = max(0.0, cd - acc.reduction)            # 그 다음 쿨감 n초(오리진 가속). 적용 범위는 기본 쿨타임 기준
    return cd

# ===== 로테이션 엔진 =====
# run()은 규칙(Rule) 목록을 위에서부터 보고, 조건이 맞는 첫 규칙의 행동을 실행한다.
# 스킬/버프가 늘어나면 run()을 고치지 않고 규칙만 추가한다.



# 전투 시작: 대기 중이던 설치기 공격(인팬트리)과 헤카테 상시 공격이 이 시각부터 시작된다
def start_combat(state):
    state.combat_started = True
    for off, s in state.combat_queue:
        schedule(state, state.t + off, 1, s)
    state.combat_queue.clear()
    if state.hecate is not None:
        schedule(state, state.t + HECATE_FIRST, 2, None)           # 헤카테 첫 공격 예약

def execute(action, state, spec):
    if action.name == ascent_action.name:                # 어센트는 3회만 쓴다: 다 썼으면 건너뛴다
        if state.ascent_left <= 0:
            return
        state.ascent_left -= 1
    if isinstance(action, Combo) and action.cooldown > 0 and action.name not in CDR_EXEMPT:
        ready_t = state.next_ready.get(action.name, 0.0)
        if state.t < ready_t - 1e-9:                     # 대기열 행동의 쿨타임이 아직 안 돌았으면 돌 때까지 기다린다
            state.trace.append((round(state.t, 3), "대기"))
            state.t = ready_t
            flush(state, state.t, spec)
    state.trace.append((round(state.t, 3), action.name))
    if isinstance(action, BuffSkill):                    # 버프 1개
        schedule(state, state.t, 0, action)
    elif isinstance(action, BuffCombo):                  # 버프 묶음: 총 딜레이 안에서 순서대로 켜진다
        for off, b in action.timeline:
            schedule(state, state.t + off, 0, b)
    else:                                                # 공격 콤보: parts를 풀어서 오프셋 시각에 발동
        if action.name == COMBAT_START and not state.combat_started:     # 버닝 브레이커 키다운 = 전투 시작
            start_combat(state)
        for h in state.attune.get(action.name, ()):      # 감응 스킬(스틱스/플레게톤)이 이 스킬과 같이 발동
            attune_cast(h, state)
        if action.name in BULLET_EMPTY_SKILLS and not maximize_active(state, state.t):     # 맥마 없이 불릿을 전부 소모 -> 첫 타격부터 장전
            state.reload_until = state.t + action.timeline[0][0] + BULLET_RELOAD
        if action.accel:                                 # 스킬 가속(오리진) 시작
            state.accels.append((state.t + action.accel.duration, action.accel))
        if action.cooldown > 0:                          # 쿨타임은 키다운(사용 시작) 시점부터. 스킬 가속이 켜져 있으면 감소
            state.next_ready[action.name] = state.t + cooldown_with_accel(action.cooldown, state.t, state, action.name)
        for off, s in action.timeline:
            if action.starts_in_combat and not state.combat_started:
                state.combat_queue.append((off - action.timeline[0][0], s))      # 전투 시작 전에는 공격하지 않고 기다린다: 첫 공격이 전투 시작 시각
            else:
                schedule(state, state.t + off, 1, s)
    state.t += action.delay
    flush(state, state.t, spec)                          # 행동이 끝난 시각까지의 이벤트 실행(delay보다 늦게 나가는 공격은 예약된 채로 남는다)


def run(spec, duration, rules, opening=(), passives=(), hecate=None, attune=None, always=(), triggers=(), ascent_spec=None, ascent_uses=None):
    state = SimState(passives=list(passives), hecate=hecate, hecate_interval=HECATE_INTERVAL,
                     hecate_end=duration, attune=dict(attune or {}), buff_duration=spec.buffDuration,
                     cooldownp=getattr(spec, 'cooldownp', 0.0), cooldown_sec=getattr(spec, 'cooldown', 0), link_triggers=list(triggers),
                     ascent_spec=ascent_spec, ascent_left=ASCENT_USES if ascent_uses is None else ascent_uses)
    state.pile_count = PILE_START_STACK                  # 시작 릴파벙 스택
    for b in always:                                     # 상시 적용 버프(컨티): 시작 시각 0부터 켜 둔다
        cast(b, state, 0.0)
    for buff in opening:
        execute(buff, state, spec)
    if not state.combat_started:                         # 오프닝에 COMBAT_START 스킬이 없으면 오프닝이 끝난 시점에 전투 시작
        start_combat(state)

    stuck = 0
    while state.t < duration:
        t_before = state.t
        for rule in rules:                      # 우선순위 순서
            if rule.when(state):
                action = rule.pick(state)
                rule.on_use(state, action)      # 게이지/스택/쿨타임 갱신
                execute(action, state, spec)
                break
        else:
            raise RuntimeError("조건이 맞는 규칙이 없음: 마지막 규칙은 항상 True여야 함")

        stuck = stuck +1 if state.t == t_before else 0
        if stuck > 20:
            raise RuntimeError(f"시간이 진행되지 않음: {state.trace[-1]} (delay=0?)")
    flush(state, math.inf, spec)                         # 마지막 행동에서 아직 안 나간 공격(설치형 등) 마무리
    state.log = [x for x in state.log if x[0] <= duration + 1e-9]       # 종료 시각 이후의 타격은 합산하지 않는다(인게임 전투분석은 종료 시점에 끊긴다)
    return state

# 조건 함수
def buff_active(state, name):
    b = state.active_buffs.get(name)
    return b is not None and b[1] > state.t

def effect_active(state):
    # 맥마의 과열 시간 감소 효과가 남아있는가(40초 이내, 13회 이내) -> 해머 사용 가능 구간
    ov = state.cd_override.get(PILE)
    return bool(ov) and ov[1] > 0 and state.t < ov[2]

# 릴파벙 사용 가능 여부
def pile_ready(state):
    return state.cannon_count >= 6 and state.t >= state.next_ready.get(PILE, 0)

# 릴파벙/버파벙 고르기: 맥마 과열 시간 감소 효과가 적용되는 사용이면 오버히트 자동 발동 버전
def pick_pile(state):
    auto = effect_active(state)
    if state.pile_count == 5:
        return burst_action_oh if auto else burst_action
    return release_action_oh if auto else release_action

# 릴파벙 스택, 오버히트 수동 사용 가능 여부
def on_pile_use(state, action):
    state.pile_count = 0 if action.name == "버스트 파일 벙커" else state.pile_count +1
    state.pile_t = state.t
    state.cannon_count = 0
    auto = effect_active(state)                  # pile_cooldown이 횟수를 차감하기 전에 판정
    state.overheat_ready = not auto              # 맥마 효과가 없을 때만 수동 오버히트 1회
    state.next_ready[PILE] = state.t + pile_cooldown(action.cooldown, state) # 쿨감 미적용, 맥마 효과만 반영

# 해머 잔여 횟수 확인
def hammer_left(state):
    lim = state.skill_uses.get("해머 스매시")
    return lim[0] if lim and state.t < lim[1] else 0

# 오버히트 수동 사용: 릴파벙 직후, 릴파벙을 쓸 수 없는 쿨타임 안에서 1회
def overheat_ready(state):
    return state.overheat_ready and state.t < state.next_ready.get(PILE, 0)

def on_overheat_use(state, action):
    state.overheat_ready = False

# 규칙 세트
pile_rule       = Rule("파일 벙커", pile_ready, pick_pile, on_pile_use)
hamm_rule     = Rule("해매팡", lambda s: effect_active(s) and hammer_left(s) > 0, lambda s: hamm_mag_fang)
mag_fang_rule   = Rule("매그팡", lambda s:True, lambda s:mag_fang)
overheat_rule   = Rule("오버히트 펀치", overheat_ready, lambda s: overheat_action, on_overheat_use)

RULES_BASIC = [pile_rule, mag_fang_rule]                # 매그팡 반복
RULES_MAXI  = [overheat_rule, pile_rule, hamm_rule, mag_fang_rule]     # 맥마 효과 중에는 해매팡


# 시나리오

def make_buff_combo(*buffs, delay):
    return BuffCombo(name="+".join(b.name for b in buffs), delay=delay, buffs=buffs)

enver_action = make_buff_combo(soul_contract, delay=MINI_BUFF_DELAY)      # 준극딜: 엔버링크 1개

def run_maxi(spec, duration=60, buff_delay=BUFF_DELAY, afterimage=True, infantry=True, aura=True, hecate_on=True):
    # (인팬트리) -> 맥마 -> 해매팡 사이클
    buffs = (maximize_cannon,) + ((afterimage_shock_bff,) if afterimage else ())
    opening = ([infantry_action] if infantry else []) + [make_buff_combo(*buffs, delay=buff_delay)]
    return run(spec, duration, RULES_MAXI, opening=opening, passives=(aura_passive,) if aura else (),
               hecate=hecate if hecate_on else None, attune=make_attune() if hecate_on else None)

# 오프닝(극딜 시작) 행동 순서: 이름 리스트로 지정한다. 순서를 바꾸고 싶으면 리스트의 이름 순서만 바꾸면 된다.

# 감응 설정: {감응시킨 스킬 이름: (같이 발동하는 헤카테 스킬들)}. 플레게톤은 헤카테 30레벨부터
def make_attune():
    out = {}
    if ATTUNE_STYX:
        out.setdefault(ATTUNE_STYX, []).append(styx_action)
    if ATTUNE_PHLEG and HECATE_LVL >= 30:
        out.setdefault(ATTUNE_PHLEG, []).append(phleg_action)
    return {k: tuple(v) for k, v in out.items()}

def make_opening(order, buff_combo):
    actions = {"인팬트리": infantry_action, "버프": buff_combo, "버브": burning_breaker_action,
               "발칸": vulkan_action, "오리진": origin_action, "엔버": enver_action, "어센트": ascent_action}
    unknown = [n for n in order if n not in actions]
    if unknown:
        raise ValueError(f"알 수 없는 행동: {unknown} / 사용 가능: {list(actions)}")
    return [actions[n] for n in order]

# ===== 재사용 규칙: 쿨타임이 돌면 극딜/준극딜을 쓴다 =====
# 극딜과 준극딜은 항상 번갈아 쓴다 (t=0 극딜 -> 준극딜 -> 극딜 -> ...)
# 우선순위: 대기열(진행 중인 극딜/준극딜) > 오버히트 > 릴파벙(쓸 수 있으면 극딜 전에 먼저) > 2분 극딜 > 1분 준극딜 > 해매팡 > 매그팡
#  2분 극딜: 인팬트리와 2분 쿨 버프(버프 시퀀스 중 쿨 100초 이상)가 모두 돌았을 때. 시작 시점에 (인팬트리->버프->버브->발칸)을 마칠 때쯤 오리진이 돌아 있으면 오리진 극딜
#  1분 준극딜: 인팬트리와 엔버링크가 돌았을 때 (버브는 시퀀스 중에 돌지 않았으면 execute가 기다린다)
def make_cycle_rules(buff_combo, order_big=ORDER_BIG, order_mini=ORDER_MINI, origin_bigs=ORIGIN_BIG_ORDER, max_wait=ORIGIN_MAX_WAIT, opening_origin=True, late_mode=ORIGIN_LATE_MODE, big_limit=None, mini_limit=None):
    big_gate  = ["인팬트리"] + [b.name for b in buff_combo.buffs if b.cooldown >= 100]
    has_enver = soul_contract.name in [b.name for b in buff_combo.buffs]        # 엔버 링크가 꺼져 있으면 준극딜에서 엔버만 빠진다(인팬트리 -> 버브)
    mini_gate = ["인팬트리"] + ([soul_contract.name] if has_enver else [])

    def ready(state, names):
        return all(state.t >= state.next_ready.get(n, 0.0) - 1e-9 for n in names)

    start_wait = Combo(name="극딜 시작 대기", delay=BURST_START_DELAY, parts=())      # 쿨이 돈 것을 확인하고 인팬트리를 누르기 전까지 아무것도 하지 않는다
    def with_wait(actions):
        return ([start_wait] if BURST_START_DELAY > 0 else []) + actions

    origin_list = sorted(origin_bigs.items())                          # [(오리진을 쓸 극딜 번호, 그 극딜의 행동 순서), ...]

    def origin_due(state):
        # 이번 극딜에서 오리진을 쓸 차례인가: 쓴 횟수 번째 오리진극의 번호에 도달했으면(미뤄진 경우 포함) 해당
        if state.origin_alone:
            return None
        k = state.origin_idx + (1 if opening_origin else 0)
        if k < len(origin_list) and state.big_count + 1 >= origin_list[k][0]:
            return origin_list[k][1]
        return None

    def origin_lag(state, order):
        # 이 극딜을 지금 시작하면 오리진을 쓰게 될 때 오리진 쿨이 아직 몇 초 남았는가
        actions = with_wait(make_opening(order, buff_combo))
        t_origin = state.t + sum(a.delay for a in actions[:[a.name for a in actions].index(origin_action.name)])
        return state.next_ready.get(origin_action.name, 0.0) - t_origin

    # 극딜/준극딜 횟수 제한: 번갈아 쓰되 횟수를 다 쓴 쪽은 건너뛴다
    def big_left(state):
        return big_limit is None or state.big_count < big_limit
    def mini_left(state):
        return mini_limit is None or state.mini_count < mini_limit
    def big_turn(state):
        return big_left(state) and (state.next_burst == "big" or not mini_left(state))
    def mini_turn(state):
        return mini_left(state) and (state.next_burst == "mini" or not big_left(state))

    def big_start_ok(state):
        if not big_turn(state) or not ready(state, big_gate):
            return False
        order = origin_due(state)
        if order is not None and 1e-9 < origin_lag(state, order) <= max_wait:
            return False                                                 # 오리진 쿨이 조금 남았다 -> 쿨이 돌 때까지 극딜 시작을 늦춘다
        return True

    def pick_big(state):
        order = origin_due(state)
        if order is not None and origin_lag(state, order) > max_wait:
            order = None                                                 # 너무 오래 기다려야 한다
            if late_mode == "단독":
                state.origin_alone = True                                # -> 오리진을 극딜과 따로, 쿨이 돌면 바로 쓴다
            # late_mode == "미루기": 오리진을 다음 극딜로 미룬다
        if order is not None:
            actions = with_wait(make_opening(order, buff_combo))
            state.origin_idx += 1
        else:
            actions = with_wait(make_opening(order_big, buff_combo))
        state.big_count += 1
        state.last_burst = "big"
        state.queue = actions[1:]
        state.next_burst = "mini"                                       # 극딜 다음은 준극딜
        return actions[0]

    def pick_mini(state):
        actions = with_wait(make_opening([n for n in order_mini if has_enver or n != "엔버"], buff_combo))
        state.queue = actions[1:]
        state.mini_t = state.t
        state.mini_count += 1
        state.last_burst = "mini"
        state.next_burst = "big"                                        # 준극딜 다음은 극딜
        return actions[0]

    queue_rule = Rule("대기열", lambda s: bool(s.queue), lambda s: s.queue.pop(0))
    # 극딜 -> 준극딜 -> 극딜 -> ... 를 번갈아 쓴다. 차례가 아닌 쪽은 쿨이 돌아도 쓰지 않고, 차례인 쪽의 쿨이 돌 때까지 평딜을 한다
    big_rule   = Rule("2분 극딜", big_start_ok, pick_big)
    mini_rule  = Rule("1분 준극딜", lambda s: mini_turn(s) and ready(s, mini_gate), pick_mini)
    def pick_origin_alone(state):
        state.origin_alone = False
        state.origin_idx += 1
        return origin_action
    alone_rule = Rule("오리진 단독", lambda s: s.origin_alone and ready(s, [origin_action.name]), pick_origin_alone)
    # 어센트: 준극딜을 쓰고 엔버링크가 끝난 뒤 ~ 다음 극딜 시작 전에서만, 릴파벙 -> 오버히트를 쓴 뒤 릴파벙이 쿨타임인 동안 매그팡 대신 쓴다 (릴파벙 쿨타임 1번에 1회)
    # 어센트가 끝나기 전에 극딜 쿨이 돌면 어센트가 극딜을 늦추므로 쓰지 않는다
    def ascent_ok(state):
        if state.ascent_left <= 0 or state.last_burst != "mini" or not big_turn(state) or state.queue:
            return False
        enver_end = state.active_buffs[soul_contract.name][1] if soul_contract.name in state.active_buffs else 0.0
        if state.t < enver_end - 1e-9 or state.pile_t < max(enver_end, state.mini_t):
            return False                                                # 엔버링크가 끝나고 나서 릴파벙을 쓴 뒤여야 한다
        cd_end = state.next_ready.get(PILE, 0.0)
        if state.t >= cd_end - 1e-9 or state.overheat_ready or state.ascent_mark == cd_end:
            return False                                                # 릴파벙이 쿨타임이어야 하고, 오버히트를 쓴 뒤여야 하고, 이 쿨타임에 아직 안 썼어야 한다
        return state.t + ascent_action.delay <= max(state.next_ready.get(n, 0.0) for n in big_gate) + 1e-9
    def on_ascent(state, action):
        state.ascent_mark = state.next_ready.get(PILE, 0.0)
    ascent_rule = Rule("어센트", ascent_ok, lambda s: ascent_action, on_ascent)
    return [queue_rule, overheat_rule, pile_rule, big_rule, mini_rule, alone_rule, ascent_rule, hamm_rule, mag_fang_rule]


def run_bunker_maxi(spec, duration=60, buff_delay=BUFF_DELAY, breaker=True, vulkan=True, afterimage=True,
                    infantry=True, aura=True, order=None, hecate_on=True,
                    extra_buffs=True, conti_on=None, restraint_on=None, reuse=True, link_on=None, fatal_on=True,
                    origin_bigs=None, origin_max_wait=None, origin_late_mode=None, ascent_uses=None, ascent_extra=None, burst_limits=None, doping_on=None):
    # ascent_extra: 어센트 계산용 스펙에 더할 스탯(CharaInfo, 분석용) / ascent_uses: 이번 실행만 어센트 사용 횟수를 바꾼다(None이면 ASCENT_USES) / origin_bigs: 이번 실행만 오리진극 {극딜 번호: 순서}를 바꾼다(None이면 ORIGIN_BIG_ORDER) / origin_max_wait / origin_late_mode: 이번 실행만 ORIGIN_MAX_WAIT / ORIGIN_LATE_MODE를 바꾼다
    # (인팬트리) -> 벙버 + 맥마 (+ 앺숔, 메여축, 리버티, 엔버링크, 리레) -> (버닝 브레이커, 발칸 펀치) -> 벙버와 해매팡 사이클
    # extra_buffs: 메여축/리버티/엔버링크 사용 여부 / conti_on, restraint_on: 시드링 ON/OFF (None이면 SEED_CONTI, SEED_RESTRAINT 값)
    # link_on: 링크 스킬 ON/OFF를 이번 실행만 바꾼다 (예: link_on={"모도": False}, 없는 링크는 LINK_ON 값). 주면 spec 인자는 무시하고 링크를 다시 계산한 스펙(base_spec_no_link 기준)을 쓴다
    big_limit, mini_limit = (BIG_COUNT, MINI_COUNT) if burst_limits is None else burst_limits      # burst_limits: 이번 실행만 (극딜 횟수, 준극딜 횟수)를 바꾼다
    if not ORIGIN_ON:                                                # 오리진 미사용: 오리진극을 없애고 첫 극딜 순서에서도 오리진을 뺀다
        origin_bigs = {}
        order = [a for a in order if a != "오리진"] if order is not None else order
    dop_on = {**DOPING_ON, **(doping_on or {})}                      # doping_on: 이번 실행만 도핑 ON/OFF를 바꾼다
    dopings = tuple(b for n, b in DOPING_BUFFS.items() if dop_on.get(n))
    links = {**LINK_ON, **(link_on or {})}
    if link_on is not None:
        spec = build_link_spec(base_spec_no_link, links)
    conti_on = SEED_CONTI if conti_on is None else conti_on
    restraint_on = SEED_RESTRAINT if restraint_on is None else restraint_on
    for g, l in ((SEED_CONTI, conti_on), (SEED_RESTRAINT, restraint_on)):     # 이번 실행만 시드링을 바꾸면 그 시드링의 스탯도 같이 더하거나 뺀다
        if g and not l:
            spec = spec - SEED_RING_STAT
        elif l and not g:
            spec = spec + SEED_RING_STAT
    buff_pool = {"벙버": bunker_buster_bff, "맥마": maximize_cannon, "앺숔": afterimage_shock_bff, "메여축": goddess_glory,
                 "리버티": liberty, "엔버": soul_contract, "리레": restraint}
    if sorted(BUFF_ORDER) != sorted(buff_pool):
        raise ValueError(f"BUFF_ORDER는 {list(buff_pool)}를 한 번씩 모두 적어야 합니다 (지금: {BUFF_ORDER})")
    buff_use = {"벙버": True, "맥마": True, "앺숔": afterimage, "메여축": extra_buffs, "리버티": extra_buffs,
                "엔버": extra_buffs and bool(links["엔버"]), "리레": bool(restraint_on)}      # 엔버링크는 링크 ON일 때, 리레는 시드링 ON일 때
    buffs = tuple(buff_pool[n] for n in BUFF_ORDER if buff_use[n])    # 버프 시퀀스 (BUFF_ORDER 순서)
    buff_combo = make_buff_combo(*buffs, delay=buff_delay)
    if order is not None:                                # order를 주면 breaker/vulkan/infantry 옵션 대신 order 순서대로 사용
        opening = make_opening(order, buff_combo)
    else:
        opening = ([infantry_action] if infantry else []) + [buff_combo]    # 인팬트리는 항상 버프 시퀀스 전에
        if breaker:
            opening.append(burning_breaker_action)
        if vulkan:
            opening.append(vulkan_action)
    rules = make_cycle_rules(buff_combo, origin_bigs=ORIGIN_BIG_ORDER if origin_bigs is None else origin_bigs,
                             max_wait=ORIGIN_MAX_WAIT if origin_max_wait is None else origin_max_wait,
                             opening_origin=bool(order) and "오리진" in order, late_mode=ORIGIN_LATE_MODE if origin_late_mode is None else origin_late_mode,
                             big_limit=big_limit, mini_limit=mini_limit) if reuse else RULES_MAXI      # reuse=True면 쿨타임이 돌 때마다 극딜/준극딜 반복
    return run(spec, duration, rules, opening=opening, passives=(aura_passive,) if aura else (),
               hecate=hecate if hecate_on else None, attune=make_attune() if hecate_on else None,
               always=dopings + ((continuous,) if conti_on else ()), ascent_spec=ascent_spec if ascent_extra is None else ascent_spec + ascent_extra, ascent_uses=ascent_uses,
               triggers=tuple(tb for name, tb in (("모도", modo_trigger), ("카인", kain_trigger)) if links[name]) + ((fatal_trigger,) if fatal_on else ()))

# ===== SIM_TIME 정하기: 지금 스펙(base_spec의 cooldown 등)에서 극딜/준극딜/오리진이 언제 시작하는지 보여준다 =====
# 이 표를 보고 위쪽 입력 셀의 SIM_TIME을 정하면 된다. (예: "극딜 3번째 시작 직전"이면 그 시각을, "오리진 쿨이 돌기 직전"이면 그 시각을 SIM_TIME에 입력)
# 시각은 인팬트리 첫 공격 기준(실제 키 입력은 선딜 INFANTRY_PRE만큼 앞). 극딜과 준극딜은 번갈아 나오므로 짝수 번째가 극딜이다.
def burst_timeline(spec=None, horizon=1500, order=None):
    spec = base_spec if spec is None else spec
    st = run_bunker_maxi(spec=spec, duration=horizon, buff_delay=BUFF_DELAY, order=ORDER_ORIGIN if order is None else order)
    df = pd.DataFrame(st.log, columns=["t", "skill", "damage"])
    inf = df[df.skill == "인팬트리"].t.tolist()
    starts = []
    for x in inf:                                   # 인팬트리는 한 번 쓰면 5초 동안 연속으로 공격하므로, 10초 넘게 떨어진 첫 공격만 사용 시작으로 본다
        if not starts or x - starts[-1] > 10:
            starts.append(x)
    ori = df[df.skill == "파이널 디스트로이어"].t.tolist()      # 오리진 타격
    ori_starts = []
    for x in ori:
        if not ori_starts or x - ori_starts[-1] > 20:
            ori_starts.append(x)
    rows = []
    for i, s in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else horizon
        used = [o for o in ori_starts if s <= o < nxt]
        rows.append({"번호": i, "종류": "극딜" if i % 2 == 0 else "준극딜", "시작(초)": round(s, 2),
                     "오리진 사용(초)": round(used[0], 2) if used else None})
    out = pd.DataFrame(rows)
    ready = [round(o + cooldown_with_accel(origin_action.cooldown, o, st, origin_action.name), 2) for o in ori_starts]
    return out, ori_starts, ready

# 사용 예 (필요할 때 주석을 풀어서 실행)
# timeline, _ori, origin_ready = burst_timeline()
# print("오리진 사용 시각(초):", [round(o, 2) for o in _ori])
# print("오리진 쿨이 도는 시각(초):", origin_ready)
# print(timeline.head(23))

# ===== 오리진극 후보 비교: 쿨감에 따라 오리진을 몇 번째 극딜에 쓸지 정할 때 쓴다 =====
# (ORIGIN_LATE_MODE = "미루기" 기준: 오리진을 극딜에 붙여서 쓰는 조합만 비교한다) 오리진극 번호 후보(1번째는 t=0 첫 극딜 고정, 나머지는 3~5극딜 간격)를 모두 돌려서 비교한다.
#  완전 = 타격이 전부 1200초 안에 들어온 오리진 횟수(4가 되어야 함) / 극딜 = 시작한 극딜 횟수(마지막 극딜은 도중에 끝나도 센다)
def origin_plan_candidates(spec=None, style=None, top=5, max_wait=99):
    spec = base_spec if spec is None else spec
    order = ORDER_ORIGIN_FIRST if style is None else style
    rows = []
    for n2 in (4, 5):
        for n3 in (n2 + 3, n2 + 4):
            for n4 in (n3 + 3, n3 + 4, n3 + 5):
                if n4 > 12:
                    continue
                nums = (1, n2, n3, n4)
                st = run_bunker_maxi(spec=spec, duration=1200, buff_delay=BUFF_DELAY, order=order,
                                     origin_bigs={n: order for n in nums}, origin_max_wait=max_wait, origin_late_mode="미루기")
                df = pd.DataFrame(st.log, columns=["t", "skill", "damage"])
                inf, hits = [], df[df.skill == "인팬트리"].t.tolist()
                for x in hits:
                    if not inf or x - inf[-1] > 10:
                        inf.append(x)
                ori, sizes, last = [], [], -1e9
                for x in df[df.skill == "파이널 디스트로이어"].t.tolist():
                    if x - last > 20:
                        ori.append(round(x, 1)); sizes.append(0)
                    sizes[-1] += 1; last = x
                full = sum(1 for s in sizes if s >= sum(n for _, n in origin_action.parts))
                rows.append({"오리진극 번호": nums, "완전": full, "극딜": len(inf[0::2]), "준극": len(inf[1::2]),
                             "오리진 시각": ori, "총딜(조)": round(df.damage.sum() / 1e12, 1)})
    out = pd.DataFrame(rows).sort_values(["완전", "극딜", "총딜(조)"], ascending=False).reset_index(drop=True)
    return out.head(top)

# 예: 현재 스펙(base_spec의 cooldown)에서 선오리진으로 쓸 때
# print(origin_plan_candidates(base_spec, ORDER_ORIGIN_FIRST))


###############################################################################################
###############################################################################################
############################### 아래부터 코드 수정 및 추가 가능 ##################################
###############################################################################################
###############################################################################################

state = run_bunker_maxi(spec=base_spec, duration=SIM_TIME, buff_delay=BUFF_DELAY, order=ORDER_ORIGIN)

dframe = pd.DataFrame(state.log, columns=["t","skill", "damage"])

