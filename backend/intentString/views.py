from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import NaturalIntentSerializer, NetworkIntentSerializer, ApplicationIntentSerializer, PolicyIntentSerializer
from .models import NaturalIntent, NetworkIntent, ApplicationIntent, PolicyIntent
from .services.intentToPolicy import map_intent_struct_to_policy, generate_yaml
import requests
import json
from django.conf import settings
import yaml
import os

# Create your views here.
def test(request):
      return HttpResponse("Test")

# 파일 저장 수행하는 함수
def safe_write_txt(filename, content):
    try:
        save_dir = os.path.join(settings.BASE_DIR, "intent_logs")
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[LOG SAVED] {file_path}")

    except Exception as e:
        print("File save skipped:", e)


#  공통: DB 없는 환경에서도 정상 작동하도록 하는 Safe Save 함수
def safe_save(serializer):
    try:
        return serializer.save()
    except Exception as e:
        print("DB save skipped:", e)
        return None

def safe_create(model, **kwargs):
    try:
        return model.objects.create(**kwargs)
    except Exception as e:
        print("DB create skipped:", e)
        return None


class NaturalIntentViewSet(viewsets.ModelViewSet):
    queryset = NaturalIntent.objects.all()
    serializer_class = NaturalIntentSerializer

    def create(self, request, *args, **kwargs):
        # 1) 프론트에서 받은 값을 serializer로 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # DB 저장을 optional 처리
        intent_obj = safe_save(serializer)

        # 전송용 payload
        payload = serializer.data

        external_url = "http://115.145.179.159:5050/infer"
        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        deploy_result = {"status": "skipped", "reason": "AI 서버 호출 실패"}
        try:
            response = requests.post(external_url, json=payload, timeout=5)
            external_response = json.loads(response.text)

            intent = external_response.get("Intent", {})
            triple = external_response.get("KGTriple", {})
            confidence = external_response.get("confidence", 1.0)

            policy = map_intent_struct_to_policy(intent, triple, confidence)
            yaml_result = generate_yaml(policy)

            safe_write_txt(
                f"policy_external.txt",
                json.dumps(external_response, indent=4, ensure_ascii=False)
            )

            safe_write_txt(
                f"policy_yaml.txt",
                yaml_result
            )

            # 리모카에 ROS2 명령 전송 (hardcoded: forward)
            # 다른 팀이 command 이름을 넘겨주면 그 이름으로 교체 예정
            command_name = "forward"
            deploy_result = {"status": "skipped", "reason": "deploy 미시도"}
            try:
                deploy_resp = requests.post(
                    "http://127.0.0.1:5000/policy/deploy",
                    json={"command": command_name},
                    timeout=15
                )
                deploy_result = deploy_resp.json()
                print(f"[DEPLOY] 리모카 전송 결과: {deploy_result}")
            except Exception as e:
                deploy_result = {"status": "failed", "message": str(e)}
                print(f"[DEPLOY] 리모카 전송 실패: {e}")

            # --- DB 저장 optional ---
            safe_create(
                PolicyIntent,
                action=intent.get("Action", ""),
                expectation_object=intent.get("ExpectationObject", ""),
                expectation_target=intent.get("ExpectationTarget", ""),
                head=triple.get("head", ""),
                relation=triple.get("relation", ""),
                tail=triple.get("tail", ""),
            )

        except Exception as e:
            external_response = f"Failed to send: {e}"


        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
            "rimoca_deploy": deploy_result,
        }, status=status.HTTP_201_CREATED)



class NetworkIntentViewSet(viewsets.ModelViewSet):
    queryset = NetworkIntent.objects.all()
    serializer_class = NetworkIntentSerializer

    def create(self, request, *args, **kwargs):

        data = request.data.get('intent')
        obj = {
            "name": data['name'],
            "mac_address": data['mac-address'],
            "ipv4_start": data['range-ipv4-address']['start'],
            "ipv4_end": data['range-ipv4-address']['end'],
            "ipv6_start": data['range-ipv6-address']['start'],
            "ipv6_end": data['range-ipv6-address']['end'],
        }

        serializer = self.get_serializer(data=obj)
        serializer.is_valid(raise_exception=True)

        # DB save optional
        intent_obj = safe_save(serializer)

        payload = {"intent": serializer.data}
        external_url = "http://115.145.179.159:5050/infer"

        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        try:
            response = requests.post(external_url, json=payload, timeout=5)
            external_response = json.loads(response.text)
        except Exception as e:
            external_response = f"Failed to send: {e}"

        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
        }, status=status.HTTP_201_CREATED)
    
class ApplicationIntentViewSet(viewsets.ModelViewSet):
    queryset = NetworkIntent.objects.all()
    serializer_class = ApplicationIntentSerializer

    def create(self, request, *args, **kwargs):

        data = request.data
        obj = {
            "user_label": data.get("user_label", ""),
            "expectation_id": data.get("expectation_id", ""),
            "expectation_verb": data.get("expectation_verb", ""),
            "object_type": data.get("object_type", ""),
            
            "context_attribute" : data["context_attributes"][0].get("contextAttribute", ""),
            "context_condition" : data["context_attributes"][0].get("contextCondition", ""),
            "context_targer_id" : data["context_attributes"][0].get("contextValueRange", ""),

            "target_name" : data["target_metrics"][0].get("targetName",""),
            "target_condition" : data["target_metrics"][0].get("targetCondition",""),
            "target_value" : data["target_metrics"][0].get("targetValueRange",""),

            "priority": data.get("priority", ""),
            "location": data.get("location", ""),
            "observation_period": data.get("observation_period", ""),
            "report_reference": data.get("report_reference", ""),
        }

        serializer = self.get_serializer(data=obj)
        serializer.is_valid(raise_exception=True)

        # DB save optional
        intent_obj = safe_save(serializer)

        payload = {"intent": serializer.data}
        external_url = "http://115.145.179.159:5050/infer"

        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        try:
            response = requests.post(external_url, json=payload, timeout=5)
            external_response = json.loads(response.text)
        except Exception as e:
            external_response = f"Failed to send: {e}"

        print("\n===== [DEBUG] External Response =====")
        print(f"External Response: {external_response}")
        print("=======================================================\n")


        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
        }, status=status.HTTP_201_CREATED)