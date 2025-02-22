import json
from pathlib import Path

from isce2_topsapp.packaging import DATASET_VERSION, get_gunw_id

test_dir = Path(__file__).parent


def test_gunw_id_generation_crossing_dateline():
    sample_json_path = test_dir / 'midnight_crossing_metadata.json'
    metadata = json.load(open(sample_json_path))
    gunw_id = get_gunw_id(metadata['reference_properties'],
                          metadata['secondary_properties'],
                          metadata['extent'])
    version_str = DATASET_VERSION.replace(".", "_")
    assert gunw_id == f'S1-GUNW-D-R-048-tops-20230106_20221214-235959-00090E_00040N-PP-c254-v{version_str}'
