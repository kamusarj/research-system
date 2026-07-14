import json


def test_training_event_governance_dataset_and_export(client):
    event = client.post(
        "/api/v1/training/events",
        json={
            "event_type": "agent-trace",
            "source": "test-suite",
            "payload": {
                "instruction": "Qualify this lead",
                "context": {"company_size": 30},
                "expected_response": "Ask for budget and timeline.",
            },
            "provenance": {"trace_id": "safe-test-trace"},
        },
    )
    assert event.status_code == 201
    example = client.post(f"/api/v1/training/events/{event.json()['id']}/convert").json()
    assert client.post(f"/api/v1/training/examples/{example['id']}/accept").status_code == 409

    checked = client.put(
        f"/api/v1/training/examples/{example['id']}",
        json={"pii_status": "anonymized", "policy_status": "approved", "split": "train"},
    )
    assert checked.status_code == 200
    assert client.post(f"/api/v1/training/examples/{example['id']}/accept").status_code == 200

    dataset = client.post(
        "/api/v1/training/datasets",
        json={"name": "Lead qualification", "version": "v1"},
    ).json()
    built = client.post(
        f"/api/v1/training/datasets/{dataset['id']}/build", json={"example_ids": [example["id"]]}
    )
    assert built.json()["example_count"] == 1
    exported = client.post(f"/api/v1/training/datasets/{dataset['id']}/export")
    assert exported.status_code == 200
    row = json.loads(exported.text.strip())
    assert row["instruction"] == "Qualify this lead"
    assert row["provenance"]["trace_id"] == "safe-test-trace"
