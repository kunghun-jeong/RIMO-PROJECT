# 1. 기본 패키지
# !pip install pyyaml

# 2. 경로 설정 (로컬 환경)
from pathlib import Path

RULES_PATH = Path("./mapping_rules.yaml")
RULES_PATH.parent.mkdir(parents=True, exist_ok=True)  # 폴더 자동 생성

# 3. 매핑 룰 작성
mapping_rules = """
Intent:
  Action: intentActions[0].actionType
  ExpectationObject: intentExpectations[0].expectationType
  ExpectationTarget: intentExpectations[0].targetMetric
  Context: intentExpectations[0].geoAreaId

KGTriple:
  head: intentExpectations[0].expectationId
  relation: intentActions[0].actionTargetOperation
  tail: intentExpectations[0].unit
""".strip()

with open(RULES_PATH, "w", encoding="utf-8") as f:
    f.write(mapping_rules)

print(f"[OK] Mapping rules saved at: {RULES_PATH.resolve()}")

# ✅ 4. 나머지 매핑 로직 (경로는 RULES_PATH 사용)
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
import yaml, json

@dataclass
class IntentExpectation:
    expectationId: str = ""
    expectationType: str = ""
    targetMetric: Optional[str] = None
    desiredChange: Optional[str] = None
    threshold: Optional[float] = None
    unit: Optional[str] = None
    geoAreaId: Optional[str] = None
    sliceId: Optional[str] = None
    startTime: Optional[str] = None
    stopTime: Optional[str] = None

@dataclass
class IntentAction:
    actionId: str = ""
    actionType: str = ""
    actionTargetOperation: str = ""

@dataclass
class IntentPolicy:
    intentId: Union[str, None] = None
    intentName: Union[str, None] = None
    intentDescription: Union[str, None] = None
    creationTime: Union[str, None] = None
    author: Union[str, None] = None
    intentStatus: Union[str, None] = None
    intentExpectations: List[IntentExpectation] = field(default_factory=list)
    intentActions: List[IntentAction] = field(default_factory=list)
    degraded: bool = False
    DegradationNote: Union[str, None] = None


# ✅ Helper functions
def prune_empty(obj):
    if isinstance(obj, dict):
        return {k: prune_empty(v) for k, v in obj.items() if v not in (None, "", [], {})}
    if isinstance(obj, list):
        return [prune_empty(v) for v in obj if v not in (None, "", [], {})]
    return obj


def load_mapping_rules(path: Path = RULES_PATH) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def apply_mapping(source: dict, policy: IntentPolicy, rules: dict) -> None:
    for src_key, target_path in rules.items():
        if src_key not in source:
            continue
        value = source[src_key]
        parts = target_path.split('.')
        obj = policy
        for idx, part in enumerate(parts):
            if '[' in part and ']' in part:
                name = part.split('[')[0]
                i = int(part[part.index('[')+1:part.index(']')])
                lst = getattr(obj, name)
                while len(lst) <= i:
                    lst.append(IntentAction() if name == 'intentActions' else IntentExpectation())
                obj = lst[i]
            else:
                if idx == len(parts) - 1:
                    setattr(obj, part, value)
                else:
                    obj = getattr(obj, part)


def map_intent_struct_to_policy(intent_struct: dict, kg_triple: dict, confidence: float,
                                threshold: float = 0.5,
                                rules_path: Path = RULES_PATH) -> IntentPolicy:
    policy = IntentPolicy(
        intentId=intent_struct.get("intentId"),
        intentName=intent_struct.get("intentName"),
        intentDescription=intent_struct.get("intentDescription"),
        creationTime=intent_struct.get("creationTime"),
        author=intent_struct.get("author"),
        intentStatus=intent_struct.get("intentStatus"),
    )
    rules = load_mapping_rules(rules_path)
    apply_mapping(intent_struct, policy, rules.get("Intent", {}))
    apply_mapping(kg_triple, policy, rules.get("KGTriple", {}))

    if confidence < threshold:
        policy.degraded = True
        policy.DegradationNote = f"Low confidence: {confidence:.2f}"
    return policy


def generate_yaml(policy: IntentPolicy) -> str:
    clean = prune_empty(asdict(policy))
    return yaml.safe_dump(clean, sort_keys=False, allow_unicode=True)


# ✅ 5. 테스트 예제
examples = [
    ("Example1", {"Action":"Block","ExpectationObject":"ServiceAccess","ExpectationTarget":"SNS","Context":"Office Hours"},
                {"head":"UserGroup_Employee","relation":"blockApplicationAccessOperation","tail":"Application_SNS"}, 0.85),

    ("Example2", {"Action":"Optimize","ExpectationObject":"Radio Network","ExpectationTarget":"Coverage","Context":"Downtown"},
                {"head":"MnS_Consumer","relation":"optimizeCoverage","tail":"RadioNetworkArea_Downtown"}, 0.78),

    ("서비스 차단",{"Action":"Block","ExpectationObject":"ServiceAccess","ExpectationTarget":"SNS","Context":"Office Hours"},
                {"head":"UserGroup_Employee","relation":"blockApplicationAccessOperation","tail":"Application_SNS"}, 0.85),

    ("커버리지 향상", {"Action":"Optimize","ExpectationObject":"Radio Network","ExpectationTarget":"Coverage","Context":"Downtown"},
                {"head":"MnS_Consumer","relation":"optimizeCoverage","tail":"RadioNetworkArea_Downtown"}, 0.78),

    ("정책 조회", {"Action":"Query","ExpectationObject":"Intent","ExpectationTarget":"Status","Context":"Group A"},
                {"head":"MnS_Consumer","relation":"queryIntent","tail":"getMOIAttribute_Operation"}, 0.92),

    ("에너지 절감", {"Action":"Reduce","ExpectationObject":"Energy Consumption","ExpectationTarget":"Power Usage","Context":"Factory Zone 3, Nighttime"},
                {"head":"FactoryController","relation":"reducePowerUsage","tail":"Zone3_PowerControlPolicy"}, 0.65),

    ("서비스 생성", {"Action":"Create","ExpectationObject":"Service Slice","ExpectationTarget":"Low Latency","Context":"Slice ID 101"},
                {"head":"MnS_Consumer","relation":"createIntent","tail":"createMOI_Operation"}, 0.99),
    ("GoStraightTest",
        {
            "Action": "Go straight",
            "ExpectationObject": "straight",
            "ExpectationTarget": "straight"
        },
        {
            "head": "AdminAgent",
            "relation": "alert",
            "tail": "intent_coverage_expansion_zoneA"
        },
        0.90)
]

for name, intent, triple, conf in examples:
    policy = map_intent_struct_to_policy(intent, triple, conf)
    
    # if name=="서비스 차단":
    yaml_data = generate_yaml(policy)
    # print(f"--- {name} YAML ---")
    # print(yaml_data)
        
    #    with open("intent.yaml", "w", encoding="utf-8") as f:
    #        f.write(yaml_data)