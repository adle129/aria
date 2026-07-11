from app.config import Settings
from app.services.manpower_baselines_store import ManpowerBaselinesStore


def test_upsert_and_query_baselines(tmp_path):
    path = tmp_path / "manpower_baselines.json"
    store = ManpowerBaselinesStore(Settings(manpower_baselines_path=str(path)))
    store.upsert_projects(
        [
            {
                "engagement_id": "eng_a",
                "project_name": "Project A",
                "source_doc": "knowledge_base/eng_a/quote.xlsx",
                "functions": {
                    "PM": {"total_man_days": 10.5, "positions": []},
                    "Chassis": {"total_man_days": 40.0, "positions": []},
                },
            }
        ]
    )
    data = store.query(engagement_id="eng_a", functions=["PM"])
    assert len(data["projects"]) == 1
    assert data["projects"][0]["functions"] == {"PM": {"total_man_days": 10.5, "positions": []}}
    assert data["updated_at"]
