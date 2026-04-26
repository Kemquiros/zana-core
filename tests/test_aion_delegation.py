from swarm.apex.aion import AionMessage, AeonDelegationRequest, AeonDelegationResponse

def test_aion_delegation_request():
    msg = AionMessage(intent="calculate", latent_state=[0.1, 0.5], payload={"x": 1})
    req = AeonDelegationRequest(
        source_aeon="zana-core",
        target_aeon="koru-os",
        task_id="task-123",
        objective="Do some calculations",
        context_payload=msg
    )
    assert req.task_id == "task-123"
    assert req.context_payload.intent == "calculate"
    print("Request validation passed.")

def test_aion_delegation_response():
    resp = AeonDelegationResponse(
        task_id="task-123",
        status="completed",
        result_payload={"result": 42},
        innovation_score=1.5
    )
    assert resp.status == "completed"
    assert resp.result_payload["result"] == 42
    print("Response validation passed.")

if __name__ == "__main__":
    test_aion_delegation_request()
    test_aion_delegation_response()