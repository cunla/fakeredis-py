import json
import math
import random
from typing import List

import pytest

from test import testtools

pytest.importorskip("numpy")

import numpy as np
import redis
from redis.commands.vectorset.commands import QuantizationOptions

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.min_server("8"),
    ]
)


def test_vgetattr_non_existing_element(r: redis.Redis):
    # Test vgetattr on a non-existing element

    assert r.vset().vgetattr("myset", "non_existing_element") is None

    # Test vgetattr on an existing element with no attributes
    r.vset().vadd("myset", [1, 2, 3], "elem1")
    attrs = r.vset().vgetattr("myset", "elem1")
    assert attrs is None

    # Test vgetattr on an existing element with attributes
    attrs_dict = {"key1": "value1", "key2": "value2"}
    r.vset().vadd("myset", [4, 5, 6], "elem2", attributes=attrs_dict)
    attrs = r.vset().vgetattr("myset", "elem2")
    assert attrs == attrs_dict


def test_vadd_same_vector_twice(r: redis.Redis):
    float_array = [1, 4.32, 0.11]
    resp = r.vset().vadd("myset", float_array, "elem1")
    assert resp == 1
    float_array = [1, 2, 3]
    resp = r.vset().vadd("myset", float_array, "elem1")
    assert resp == 0
    resp = r.vset().vrandmember("myset")
    assert resp == b"elem1"


def test_add_elem_with_values(r: redis.Redis):
    float_array = [1, 4.32, 0.11]
    resp = r.vset().vadd("myset", float_array, "elem1")
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization(float_array, emb, tolerance=0.1)

    with pytest.raises(redis.DataError):
        r.vset().vadd("myset_invalid_data", None, "elem1")

    with pytest.raises(redis.DataError):
        r.vset().vadd("myset_invalid_data", [12, 45], None, reduce_dim=3)


def test_add_elem_with_vector(r: redis.Redis):
    float_array = [1, 4.32, 0.11]
    # Convert the list of floats to a byte array in fp32 format
    byte_array = _to_fp32_blob_array(float_array)
    resp = r.vset().vadd("myset", byte_array, "elem1")
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization(float_array, emb, tolerance=0.1)


def test_add_elem_reduced_dim(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9]
    resp = r.vset().vadd("myset", float_array, "elem1", reduce_dim=3)
    assert resp == 1

    dim = r.vset().vdim("myset")
    assert dim == 3


def test_add_elem_cas(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9]
    resp = r.vset().vadd("myset", vector=float_array, element="elem1", cas=True)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization(float_array, emb, tolerance=0.1)


def test_add_elem_no_quant(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9]
    resp = r.vset().vadd("myset", vector=float_array, element="elem1", quantization=QuantizationOptions.NOQUANT)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization(float_array, emb, tolerance=0.0)


def test_add_elem_bin_quant(r: redis.Redis):
    float_array = [1, 4.32, 0.0, 0.05, -2.9]
    resp = r.vset().vadd("myset", vector=float_array, element="elem1", quantization=QuantizationOptions.BIN)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization([1, 1, -1, 1, -1], emb, tolerance=0.0)


def test_add_elem_q8_quant(r: redis.Redis):
    float_array = [1, 4.32, 10.0, -21, -2.9]
    resp = r.vset().vadd("myset", vector=float_array, element="elem1", quantization=QuantizationOptions.Q8)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem1")
    assert _validate_quantization(float_array, emb, tolerance=0.1)


def test_add_elem_ef(r: redis.Redis):
    r.vset().vadd("myset", vector=[5, 55, 65, -20, 30], element="elem1")
    r.vset().vadd("myset", vector=[-40, -40.32, 10.0, -4, 2.9], element="elem2")

    float_array = [1, 4.32, 10.0, -21, -2.9]
    resp = r.vset().vadd("myset", float_array, "elem3", ef=1)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem3")
    assert _validate_quantization(float_array, emb, tolerance=0.1)

    sim = r.vset().vsim("myset", input="elem3", with_scores=True)
    assert len(sim) == 3


def test_add_elem_with_attr(r: redis.Redis):
    float_array = [1, 4.32, 10.0, -21, -2.9]
    attrs_dict = {"key1": "value1", "key2": "value2"}
    resp = r.vset().vadd("myset", vector=float_array, element="elem3", attributes=attrs_dict)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem3")
    assert _validate_quantization(float_array, emb, tolerance=0.1)

    attr_saved = r.vset().vgetattr("myset", "elem3")
    assert attr_saved == attrs_dict

    resp = r.vset().vadd("myset", vector=float_array, element="elem4", attributes={})
    assert resp == 1

    emb = r.vset().vemb("myset", "elem4")
    assert _validate_quantization(float_array, emb, tolerance=0.1)

    attr_saved = r.vset().vgetattr("myset", "elem4")
    assert attr_saved is None

    resp = r.vset().vadd("myset", vector=float_array, element="elem5", attributes=json.dumps(attrs_dict))
    assert resp == 1

    emb = r.vset().vemb("myset", "elem5")
    assert _validate_quantization(float_array, emb, tolerance=0.1)

    attr_saved = r.vset().vgetattr("myset", "elem5")
    assert attr_saved == attrs_dict


def test_add_elem_with_numlinks(r: redis.Redis):
    elements_count = 100
    vector_dim = 10
    for i in range(elements_count):
        float_array = [random.randint(0, 10) for x in range(vector_dim)]
        r.vset().vadd("myset", float_array, f"elem{i}", numlinks=8)

    float_array = [1, 4.32, 0.11, 0.5, 0.9, 0.1, 0.2, 0.3, 0.4, 0.5]
    resp = r.vset().vadd("myset", float_array, "elem_numlinks", numlinks=8)
    assert resp == 1

    emb = r.vset().vemb("myset", "elem_numlinks")
    assert _validate_quantization(float_array, emb, tolerance=0.5)

    numlinks_all_layers = r.vset().vlinks("myset", "elem_numlinks")
    for neighbours_list_for_layer in numlinks_all_layers:
        assert len(neighbours_list_for_layer) <= 8


def test_vsim_count(r: redis.Redis):
    elements_count = 30
    vector_dim = 800
    for i in range(elements_count):
        float_array = [random.uniform(0, 10) for x in range(vector_dim)]
        r.vset().vadd("myset", float_array, f"elem{i}", numlinks=64)

    vsim = r.vset().vsim("myset", input="elem1")
    assert len(vsim) == 10
    assert isinstance(vsim, list)
    assert isinstance(vsim[0], bytes)

    vsim = r.vset().vsim("myset", input="elem1", count=5)
    assert len(vsim) == 5
    assert isinstance(vsim, list)
    assert isinstance(vsim[0], bytes)

    vsim = r.vset().vsim("myset", input="elem1", count=50)
    assert len(vsim) == 30
    assert isinstance(vsim, list)
    assert isinstance(vsim[0], bytes)

    vsim = r.vset().vsim("myset", input="elem1", count=15)
    assert len(vsim) == 15
    assert isinstance(vsim, list)
    assert isinstance(vsim[0], bytes)


def test_vsim_with_scores(r: redis.Redis):
    elements_count = 20
    vector_dim = 50
    for i in range(elements_count):
        float_array = [random.uniform(0, 10) for x in range(vector_dim)]
        r.vset().vadd("myset", float_array, f"elem{i}", numlinks=64)

    vsim = r.vset().vsim("myset", input="elem1", with_scores=True)
    assert len(vsim) == 10
    assert isinstance(vsim, dict)
    assert isinstance(vsim[b"elem1"], float)
    assert vsim[b"elem1"] >= 0.99


def test_vsim_with_different_vector_input_types(r: redis.Redis):
    elements_count = 10
    vector_dim = 5
    for i in range(elements_count):
        float_array = [random.uniform(0, 10) for x in range(vector_dim)]
        attributes = {"index": i, "elem_name": f"elem_{i}"}
        r.vset().vadd("myset", float_array, f"elem_{i}", numlinks=4, attributes=attributes)
    sim = r.vset().vsim("myset", input="elem_1")
    assert len(sim) == 10
    assert isinstance(sim, list)

    float_array = [1, 4.32, 0.0, 0.05, -2.9]
    sim_to_float_array = r.vset().vsim("myset", input=float_array)
    assert len(sim_to_float_array) == 10
    assert isinstance(sim_to_float_array, list)

    fp32_vector = _to_fp32_blob_array(float_array)
    sim_to_fp32_vector = r.vset().vsim("myset", input=fp32_vector)
    assert len(sim_to_fp32_vector) == 10
    assert isinstance(sim_to_fp32_vector, list)
    assert sim_to_float_array == sim_to_fp32_vector

    with pytest.raises(redis.DataError):
        r.vset().vsim("myset", input=None)


def test_vsim_unexisting(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9]
    r.vset().vadd("myset", vector=float_array, element="elem1", cas=True)

    with pytest.raises(redis.ResponseError) as exc_info:
        r.vset().vsim("myset", input="elem_not_existing")

    assert str(exc_info.value) == "element not found in set"
    sim = r.vset().vsim("myset_not_existing", input="elem1")
    assert sim == []


def test_vsim_with_filter(r: redis.Redis):
    elements_count = 50
    vector_dim = 800
    for i in range(elements_count):
        float_array = [random.uniform(10, 20) for x in range(vector_dim)]
        attributes = {"index": i, "elem_name": f"elem_{i}"}
        r.vset().vadd("myset", float_array, f"elem_{i}", numlinks=4, attributes=attributes)
    float_array = [-random.uniform(10, 20) for x in range(vector_dim)]
    attributes = {"index": elements_count, "elem_name": "elem_special"}
    r.vset().vadd("myset", float_array, "elem_special", numlinks=4, attributes=attributes)
    sim = r.vset().vsim("myset", input="elem_1", filter=".index > 10")
    assert len(sim) == 10
    assert isinstance(sim, list)
    for elem in sim:
        assert int(elem.split(b"_")[1]) > 10

    sim = r.vset().vsim(
        "myset", input="elem_1", filter=".index > 10 and .index < 15 and .elem_name in ['elem_12', 'elem_17']"
    )
    assert len(sim) == 1
    assert isinstance(sim, list)
    assert sim[0] == b"elem_12"

    sim = r.vset().vsim(
        "myset", input="elem_1", filter=".index > 25 and .elem_name in ['elem_12', 'elem_17', 'elem_19']", ef=100
    )
    assert len(sim) == 0
    assert isinstance(sim, list)

    # todo filter_ef

    # sim = r.vset().vsim(
    #     "myset",
    #     input="elem_1",
    #     filter=".index > 28 and .elem_name in ['elem_12', 'elem_17', 'elem_special']",
    #     filter_ef=1,
    # )
    # assert len(sim) == 0, f"Expected 0 results, but got {len(sim)} with filter_ef=1, sim: {sim}"
    # assert isinstance(sim, list)

    sim = r.vset().vsim(
        "myset",
        input="elem_1",
        filter=".index > 28 and .elem_name in ['elem_12', 'elem_17', 'elem_special']",
        filter_ef=500,
    )
    assert len(sim) == 1
    assert isinstance(sim, list)


#
# def test_vsim_truth_no_thread_enabled(r: redis.Redis):
#     elements_count = 5000
#     vector_dim = 50
#     for i in range(1, elements_count + 1):
#         float_array = [random.uniform(10 * i, 1000 * i) for x in range(vector_dim)]
#         r.vset().vadd("myset", float_array, f"elem_{i}")
#
#     r.vset().vadd("myset", [-22 for _ in range(vector_dim)], "elem_man_2")
#
#     sim_without_truth = r.vset().vsim("myset", input="elem_man_2", with_scores=True)
#     sim_truth = r.vset().vsim("myset", input="elem_man_2", with_scores=True, truth=True)
#
#     assert len(sim_without_truth) == 10
#     assert len(sim_truth) == 10
#
#     assert isinstance(sim_without_truth, dict)
#     assert isinstance(sim_truth, dict)
#
#     results_scores = list(zip([v for _, v in sim_truth.items()], [v for _, v in sim_without_truth.items()]))
#
#     found_better_match = False
#     for score_with_truth, score_without_truth in results_scores:
#         if score_with_truth < score_without_truth:
#             assert False, "Score with truth [{score_with_truth}] < score without truth [{score_without_truth}]"
#         elif score_with_truth > score_without_truth:
#             found_better_match = True
#
#     assert found_better_match
#
#     sim_no_thread = r.vset().vsim("myset", input="elem_man_2", with_scores=True, no_thread=True)
#
#     assert len(sim_no_thread) == 10
#     assert isinstance(sim_no_thread, dict)


def test_vdim(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9, 0.1, 0.2]
    r.vset().vadd("myset", float_array, "elem1")

    dim = r.vset().vdim("myset")
    assert dim == len(float_array)

    r.vset().vadd("myset_reduced", float_array, "elem1", reduce_dim=4)
    reduced_dim = r.vset().vdim("myset_reduced")
    assert reduced_dim == 4

    with pytest.raises(redis.ResponseError):
        r.vset().vdim("myset_unexisting")


def test_vdim_errors(r: redis.Redis):
    float_array = [1, 4.32, 0.11, 0.5, 0.9, 0.1, 0.2]
    r.vset().vadd("myset", float_array, "elem1")

    dim = r.vset().vdim("myset")
    assert dim == len(float_array)
    with pytest.raises(redis.ResponseError) as ctx:
        r.vset().vadd("myset", float_array, "elem2", reduce_dim=4)
    assert str(ctx.value) == "cannot add projection to existing set without projection"

    float_array = [1, 4.32, 0.11, 0.5, 0.9, 0.1, 0.2]
    with pytest.raises(redis.ResponseError) as ctx:
        r.vset().vadd("myset1", float_array, "elem1", reduce_dim=-4)
    assert str(ctx.value) == "invalid vector specification"


def test_vcard(r: redis.Redis):
    n = 20
    for i in range(n):
        float_array = [random.uniform(0, 10) for x in range(1, 8)]
        r.vset().vadd("myset", float_array, f"elem{i}")

    card = r.vset().vcard("myset")
    assert card == n

    with pytest.raises(redis.ResponseError):
        r.vset().vdim("myset_unexisting")


def test_vrem(r: redis.Redis):
    n = 3
    for i in range(n):
        float_array = [random.uniform(0, 10) for x in range(1, 8)]
        vadd_res = r.vset().vadd("myset", float_array, f"elem{i}")
        assert vadd_res == 1

    resp = r.vset().vrem("myset", "elem2")
    assert resp == 1

    card = r.vset().vcard("myset")
    assert card == n - 1

    resp = r.vset().vrem("myset", "elem2")
    assert resp == 0

    card = r.vset().vcard("myset")
    assert card == n - 1

    resp = r.vset().vrem("myset_unexisting", "elem1")
    assert resp == 0


def test_vemb_bin_quantization(r: redis.Redis):
    e = [1, 4.32, 0.0, 0.05, -2.9]
    r.vset().vadd("myset", e, "elem", quantization=QuantizationOptions.BIN)
    emb_no_quant = r.vset().vemb("myset", "elem")
    assert emb_no_quant == [1, 1, -1, 1, -1]

    emb_no_quant_raw = r.vset().vemb("myset", "elem", raw=True)
    assert emb_no_quant_raw["quantization"] == b"bin"
    assert isinstance(emb_no_quant_raw["raw"], bytes)
    assert isinstance(emb_no_quant_raw["l2"], float)
    assert emb_no_quant_raw["l2"] == pytest.approx(5.29, rel=0.01)
    assert "range" not in emb_no_quant_raw


def test_vemb_q8_quantization(r: redis.Redis):
    e = [1, 10.32, 0.0, 2.05, -12.5]
    r.vset().vadd("myset", e, "elem", quantization=QuantizationOptions.Q8)

    emb_q8_quant = r.vset().vemb("myset", "elem")
    assert _validate_quantization(e, emb_q8_quant, tolerance=0.1)

    emb_q8_quant_raw = r.vset().vemb("myset", "elem", raw=True)
    assert emb_q8_quant_raw["quantization"] == b"int8"
    assert isinstance(emb_q8_quant_raw["raw"], bytes)
    assert isinstance(emb_q8_quant_raw["l2"], float)
    assert emb_q8_quant_raw["l2"] == pytest.approx(16.369, rel=0.01)
    assert isinstance(emb_q8_quant_raw["range"], float)
    assert emb_q8_quant_raw["range"] == pytest.approx(0.76, rel=0.01)


def test_vemb_no_quantization(r: redis.Redis):
    e = [1, 10.32, 0.0, 2.05, -12.5]
    r.vset().vadd("myset", e, "elem", quantization=QuantizationOptions.NOQUANT)

    emb_no_quant = r.vset().vemb("myset", "elem")
    assert _validate_quantization(e, emb_no_quant, tolerance=0.1)

    emb_no_quant_raw = r.vset().vemb("myset", "elem", raw=True)
    assert emb_no_quant_raw["quantization"] == b"f32"
    assert isinstance(emb_no_quant_raw["raw"], bytes)
    assert isinstance(emb_no_quant_raw["l2"], float)
    assert "range" not in emb_no_quant_raw


def test_vemb_default_quantization(r: redis.Redis):
    e = [1, 5.32, 0.0, 0.25, -5]
    r.vset().vadd("myset", vector=e, element="elem")

    emb_default_quant = r.vset().vemb("myset", "elem")
    assert _validate_quantization(e, emb_default_quant, tolerance=0.1)

    emb_default_quant_raw = r.vset().vemb("myset", "elem", raw=True)
    assert emb_default_quant_raw["quantization"] == b"int8"
    assert isinstance(emb_default_quant_raw["raw"], bytes)
    assert isinstance(emb_default_quant_raw["l2"], float)
    assert isinstance(emb_default_quant_raw["range"], float)


def test_vemb_fp32_quantization(r: redis.Redis):
    float_array_fp32 = [1, 4.32, 0.11]
    # Convert the list of floats to a byte array in fp32 format
    byte_array = _to_fp32_blob_array(float_array_fp32)
    r.vset().vadd("myset", byte_array, "elem")

    emb_fp32_quant = r.vset().vemb("myset", "elem")
    assert _validate_quantization(float_array_fp32, emb_fp32_quant, tolerance=0.1)

    emb_fp32_quant_raw = r.vset().vemb("myset", "elem", raw=True)
    assert emb_fp32_quant_raw["quantization"] == b"int8"
    assert isinstance(emb_fp32_quant_raw["raw"], bytes)
    assert isinstance(emb_fp32_quant_raw["l2"], float)
    assert isinstance(emb_fp32_quant_raw["range"], float)


def test_vemb_unexisting(r: redis.Redis):
    emb_not_existing = r.vset().vemb("not_existing", "elem")
    assert emb_not_existing is None

    e = [1, 5.32, 0.0, 0.25, -5]
    r.vset().vadd("myset", vector=e, element="elem")
    emb_elem_not_existing = r.vset().vemb("myset", "not_existing")
    assert emb_elem_not_existing is None


def test_vlinks(r: redis.Redis):
    elements_count = 100
    vector_dim = 800
    for i in range(elements_count):
        float_array = [random.uniform(0, 10) for x in range(vector_dim)]
        r.vset().vadd("myset", float_array, f"elem{i}", numlinks=8)

    element_links_all_layers = r.vset().vlinks("myset", "elem1")
    assert len(element_links_all_layers) >= 1
    for neighbours_list_for_layer in element_links_all_layers:
        assert isinstance(neighbours_list_for_layer, list)
        for neighbour in neighbours_list_for_layer:
            assert isinstance(neighbour, bytes)

    elem_links_all_layers_with_scores = r.vset().vlinks("myset", "elem1", with_scores=True)
    assert len(elem_links_all_layers_with_scores) >= 1
    for neighbours_dict_for_layer in elem_links_all_layers_with_scores:
        assert isinstance(neighbours_dict_for_layer, dict)
        for neighbour_key, score_value in neighbours_dict_for_layer.items():
            assert isinstance(neighbour_key, bytes)
            assert isinstance(score_value, float)

    float_array = [0.75, 0.25, 0.5, 0.1, 0.9]
    r.vset().vadd("myset_one_elem_only", float_array, "elem1")
    elem_no_neighbours_with_scores = r.vset().vlinks("myset_one_elem_only", "elem1", with_scores=True)
    assert len(elem_no_neighbours_with_scores) >= 1
    for neighbours_dict_for_layer in elem_no_neighbours_with_scores:
        assert isinstance(neighbours_dict_for_layer, dict)
        assert len(neighbours_dict_for_layer) == 0

    elem_no_neighbours_no_scores = r.vset().vlinks("myset_one_elem_only", "elem1")
    assert len(elem_no_neighbours_no_scores) >= 1
    for neighbours_list_for_layer in elem_no_neighbours_no_scores:
        assert isinstance(neighbours_list_for_layer, list)
        assert len(neighbours_list_for_layer) == 0

    unexisting_element_links = r.vset().vlinks("myset", "unexisting_elem")
    assert unexisting_element_links is None

    unexisting_vset_links = r.vset().vlinks("myset_unexisting", "elem1")
    assert unexisting_vset_links is None

    unexisting_element_links = r.vset().vlinks("myset", "unexisting_elem", with_scores=True)
    assert unexisting_element_links is None

    unexisting_vset_links = r.vset().vlinks("myset_unexisting", "elem1", with_scores=True)
    assert unexisting_vset_links is None


def test_vinfo(r: redis.Redis):
    elements_count = 100
    vector_dim = 800
    for i in range(elements_count):
        float_array = [random.uniform(0, 10) for x in range(vector_dim)]
        r.vset().vadd("myset", float_array, f"elem{i}", numlinks=8, quantization=QuantizationOptions.BIN)

    vset_info = r.vset().vinfo("myset")
    assert vset_info[b"quant-type"] == b"bin"
    assert vset_info[b"vector-dim"] == vector_dim
    assert vset_info[b"size"] == elements_count
    assert vset_info[b"max-level"] > 0
    assert vset_info[b"hnsw-max-node-uid"] == elements_count

    unexisting_vset_info = r.vset().vinfo("myset_unexisting")
    assert unexisting_vset_info is None


def test_vset_vget_attributes(r: redis.Redis):
    float_array = [1, 4.32, 0.11]
    attributes = {"key1": "value1", "key2": "value2"}

    # validate vgetattrs when no attributes are set with vadd
    resp = r.vset().vadd("myset", float_array, "elem1")
    assert resp == 1

    attrs = r.vset().vgetattr("myset", "elem1")
    assert attrs is None

    # validate vgetattrs when attributes are set with vadd
    resp = r.vset().vadd("myset_with_attrs", float_array, "elem1", attributes=attributes)
    assert resp == 1

    attrs = r.vset().vgetattr("myset_with_attrs", "elem1")
    assert attrs == attributes

    # Set attributes and get attributes
    resp = r.vset().vsetattr("myset", "elem1", attributes)
    assert resp == 1
    attr_saved = r.vset().vgetattr("myset", "elem1")
    assert attr_saved == attributes

    # Set attributes to None
    resp = r.vset().vsetattr("myset", "elem1", None)
    assert resp == 1
    attr_saved = r.vset().vgetattr("myset", "elem1")
    assert attr_saved is None

    # Set attributes to empty dict
    resp = r.vset().vsetattr("myset", "elem1", {})
    assert resp == 1
    attr_saved = r.vset().vgetattr("myset", "elem1")
    assert attr_saved is None

    # Set attributes provided as string
    resp = r.vset().vsetattr("myset", "elem1", json.dumps(attributes))
    assert resp == 1
    attr_saved = r.vset().vgetattr("myset", "elem1")
    assert attr_saved == attributes

    # Set attributes to unexisting element
    resp = r.vset().vsetattr("myset", "elem2", attributes)
    assert resp == 0
    attr_saved = r.vset().vgetattr("myset", "elem2")
    assert attr_saved is None

    # Set attributes to unexisting vset
    resp = r.vset().vsetattr("myset_unexisting", "elem1", attributes)
    assert resp == 0
    attr_saved = r.vset().vgetattr("myset_unexisting", "elem1")
    assert attr_saved is None


def test_vrandmember(r: redis.Redis):
    elements = ["elem1", "elem2", "elem3"]
    for elem in elements:
        float_array = [random.uniform(0, 10) for x in range(1, 8)]
        r.vset().vadd("myset", float_array, element=elem)

    random_member = r.vset().vrandmember("myset")
    assert random_member.decode() in elements

    members_list: List[bytes] = r.vset().vrandmember("myset", count=2)
    assert len(members_list) == 2
    assert all(member.decode() in elements for member in members_list)

    # Test with count greater than the number of elements
    members_list = r.vset().vrandmember("myset", count=10)
    assert len(members_list) == len(elements)
    assert all(member.decode() in elements for member in members_list)

    # Test with negative count
    members_list = r.vset().vrandmember("myset", count=-2)
    assert len(members_list) == 2
    assert all(member.decode() in elements for member in members_list)

    # Test with count equal to the number of elements
    members_list = r.vset().vrandmember("myset", count=len(elements))
    assert len(members_list) == len(elements)
    assert all(member.decode() in elements for member in members_list)

    # Test with count equal to 0
    members_list = r.vset().vrandmember("myset", count=0)
    assert members_list == []

    # Test with count equal to 1
    members_list = r.vset().vrandmember("myset", count=1)
    assert len(members_list) == 1
    assert members_list[0].decode() in elements

    # Test with count equal to -1
    members_list = r.vset().vrandmember("myset", count=-1)
    assert len(members_list) == 1
    assert members_list[0].decode() in elements

    # Test with unexisting vset & without count
    members_list = r.vset().vrandmember("myset_unexisting")
    assert members_list is None

    # Test with unexisting vset & count
    members_list = r.vset().vrandmember("myset_unexisting", count=5)
    assert members_list == []


def test_vrandmember_wrong_type(r: redis.Redis):
    # Test with non vset value
    r.set("not_a_vset", "some_value")
    with pytest.raises(redis.ResponseError) as excinfo:
        r.vset().vrandmember("not_a_vset")
    assert excinfo.value.args[0] == "WRONGTYPE Operation against a key holding the wrong kind of value"


def test_randmember_bad_count_type(r: redis.Redis):
    # Test with bad count type
    elements = ["elem1", "elem2", "elem3"]
    for elem in elements:
        float_array = [random.uniform(0, 10) for x in range(1, 8)]
        r.vset().vadd("myset", float_array, element=elem)
    with pytest.raises(redis.ResponseError) as excinfo:
        r.vset().vrandmember("myset", count="not_an_integer")
    assert excinfo.value.args[0] == "COUNT value is not an integer"


@pytest.mark.fake
def test_vset_commands_without_decoding_responses(r: redis.Redis):
    # test vadd
    elements = ["elem1", "elem2", "elem3"]
    for elem in elements:
        float_array = [random.uniform(0.5, 10) for x in range(0, 8)]
        resp = r.vset().vadd("myset", float_array, element=elem)
        assert resp == 1

    # test vemb
    emb = r.vset().vemb("myset", "elem1")
    assert len(emb) == 8
    assert isinstance(emb, list)
    assert all(isinstance(x, float) for x in emb), f"Expected float values, got {emb}"

    emb_raw = r.vset().vemb("myset", "elem1", raw=True)
    assert emb_raw["quantization"] == b"int8"
    assert isinstance(emb_raw["raw"], bytes)
    assert isinstance(emb_raw["l2"], float)
    assert isinstance(emb_raw["range"], float)

    # test vsim
    vsim = r.vset().vsim("myset", input="elem1")
    assert len(vsim) == 3
    assert isinstance(vsim, list)
    assert isinstance(vsim[0], bytes)

    # test vsim with scores
    vsim_with_scores = r.vset().vsim("myset", input="elem1", with_scores=True)
    assert len(vsim_with_scores) == 3
    assert isinstance(vsim_with_scores, dict)
    assert isinstance(vsim_with_scores[b"elem1"], float)

    # test vsim with scores with attributes
    vsim_with_scores = r.vset().vsim("myset", input="elem1", with_scores=True, with_attribs=True)
    assert len(vsim_with_scores) == 3
    assert isinstance(vsim_with_scores, dict)
    assert len(vsim_with_scores) == 3
    assert isinstance(vsim_with_scores, dict)
    assert isinstance(vsim_with_scores[b"elem1"], dict)
    assert vsim_with_scores[b"elem1"]["attributes"] is None
    assert isinstance(vsim_with_scores[b"elem1"]["score"], float)

    # test vsim with attributes
    vsim_with_scores = r.vset().vsim("myset", input="elem1", with_attribs=True)
    assert len(vsim_with_scores) == 3
    assert isinstance(vsim_with_scores, dict)
    assert len(vsim_with_scores) == 3
    assert isinstance(vsim_with_scores, dict)
    assert vsim_with_scores[b"elem1"] is None

    # test vlinks - no scores
    element_links_all_layers = r.vset().vlinks("myset", "elem1")
    assert len(element_links_all_layers) >= 1
    for neighbours_list_for_layer in element_links_all_layers:
        assert isinstance(neighbours_list_for_layer, list)
        for neighbour in neighbours_list_for_layer:
            assert isinstance(neighbour, bytes)
    # test vlinks with scores
    elem_links_all_layers_with_scores = r.vset().vlinks("myset", "elem1", with_scores=True)
    assert len(elem_links_all_layers_with_scores) >= 1
    for neighbours_dict_for_layer in elem_links_all_layers_with_scores:
        assert isinstance(neighbours_dict_for_layer, dict)
        for neighbour_key, score_value in neighbours_dict_for_layer.items():
            assert isinstance(neighbour_key, bytes)
            assert isinstance(score_value, float)

    # test vinfo
    vset_info = r.vset().vinfo("myset")
    assert vset_info[b"quant-type"] == b"int8"
    assert vset_info[b"vector-dim"] == 8
    assert vset_info[b"size"] == len(elements)
    assert vset_info[b"max-level"] >= 0
    assert vset_info[b"hnsw-max-node-uid"] == len(elements)

    # test vgetattr
    attributes = {"key1": "value1", "key2": "value2"}
    r.vset().vsetattr("myset", "elem1", attributes)
    attrs = r.vset().vgetattr("myset", "elem1")
    assert attrs == attributes

    # test vrandmember
    random_member = r.vset().vrandmember("myset")
    assert isinstance(random_member, bytes)
    assert random_member.decode("utf-8") in elements

    members_list = r.vset().vrandmember("myset", count=2)
    assert len(members_list) == 2
    assert all(member.decode("utf-8") in elements for member in members_list)


def _to_fp32_blob_array(float_array):
    """
    Convert a list of floats to a byte array in fp32 format.
    """
    # Convert the list of floats to a NumPy array with dtype np.float32
    arr = np.array(float_array, dtype=np.float32)
    # Convert the NumPy array to a byte array
    byte_array = arr.tobytes()
    return byte_array


def _validate_quantization(original, quantized, tolerance=0.1):
    original = np.array(original, dtype=np.float32)
    quantized = np.array(quantized, dtype=np.float32)

    max_diff = np.max(np.abs(original - quantized))
    return max_diff <= tolerance


@testtools.run_test_if_redispy_ver("gte", "7.2")
@pytest.mark.min_server("8.4")
def test_vrange_basic(r: redis.Redis):
    """Test basic VRANGE functionality with lexicographical ordering."""
    # Add elements with different names
    elements = [b"apple", b"banana", b"cherry", b"date", b"elderberry"]
    for elem in elements:
        r.vset().vadd(b"myset", [1.0, 2.0, 3.0], elem)

    # Test full range
    result = r.vset().vrange(b"myset", "-", "+")
    assert result == elements
    assert len(result) == 5

    # Test inclusive range
    result = r.vset().vrange(b"myset", "[banana", "[date")
    assert result == [b"banana", b"cherry", b"date"]

    # Test exclusive range
    result = r.vset().vrange("myset", "(banana", "(date")
    assert result == [b"cherry"]


@testtools.run_test_if_redispy_ver("gte", "7.2")
@pytest.mark.min_server("8.4")
def test_vrange_error(r: redis.Redis):
    r.set("not_a_vset", "some_value")
    with pytest.raises(redis.ResponseError) as excinfo:
        r.vset().vrange("not_a_vset", "-", "+")
    assert excinfo.value.args[0] == "WRONGTYPE Operation against a key holding the wrong kind of value"

    res = r.vset().vrange("x", "-", "+")
    assert res == []


@testtools.run_test_if_redispy_ver("gte", "7.2")
@pytest.mark.min_server("8.4")
def test_vrange_with_count(r: redis.Redis):
    """Test VRANGE with count parameter."""
    # Add elements
    elements = [b"a", b"b", b"c", b"d", b"e", b"f", b"g"]
    for elem in elements:
        r.vset().vadd("myset", [1.0, 2.0], elem)

    # Test with positive count
    result = r.vset().vrange("myset", "-", "+", count=3)
    assert len(result) == 3
    assert result == [b"a", b"b", b"c"]

    # Test with count larger than set size
    result = r.vset().vrange("myset", "-", "+", count=100)
    assert len(result) == 7
    assert result == elements

    # Test with count = 0
    result = r.vset().vrange("myset", "-", "+", count=0)
    assert result == []

    # Test with negative count (should return all)
    result = r.vset().vrange("myset", "-", "+", count=-1)
    assert len(result) == 7
    assert result == elements


def test_vsim_cosine_scores(r: redis.Redis):
    """Test exact cosine similarity scores using NOQUANT with unit vectors."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "same", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "orthogonal", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "opposite", quantization=QuantizationOptions.NOQUANT)

    result = r.vset().vsim("myset", input="same", with_scores=True, count=3)

    assert list(result.keys()) == [b"same", b"orthogonal", b"opposite"]
    assert result[b"same"] == pytest.approx(1.0, abs=0.001)
    assert result[b"orthogonal"] == pytest.approx(0.5, abs=0.01)
    assert result[b"opposite"] == pytest.approx(0.0, abs=0.001)


def test_vsim_cosine_diagonal(r: redis.Redis):
    """Test cosine similarity equals 1/sqrt(2) for a 45-degree vector."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "x_axis", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [1.0, 1.0, 0.0], "diagonal", quantization=QuantizationOptions.NOQUANT)

    result = r.vset().vsim("myset", input="x_axis", with_scores=True, count=2)

    assert list(result.keys()) == [b"x_axis", b"diagonal"]
    assert result[b"x_axis"] == pytest.approx(1.0, abs=0.001)
    assert result[b"diagonal"] == pytest.approx((1.0 + 1.0 / math.sqrt(2)) / 2, abs=0.01)


def test_vsim_fp32_input_scores(r: redis.Redis):
    """Test that querying by float array gives the same scores as querying by element name."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "c", quantization=QuantizationOptions.NOQUANT)

    by_name = r.vset().vsim("myset", input="a", with_scores=True, count=3)
    by_vector = r.vset().vsim("myset", input=[1.0, 0.0, 0.0], with_scores=True, count=3)

    assert list(by_name.keys()) == list(by_vector.keys())
    for key in by_name:
        assert by_name[key] == pytest.approx(by_vector[key], abs=0.001)


def test_vsim_count_exact(r: redis.Redis):
    """Test vsim count with 5 NOQUANT vectors whose similarity ordering is precisely known."""
    # Cosine similarities to [1, 0, 0]: a=1.0, b≈0.994, c≈0.707, d=0.0, e=-1.0
    for name, vec in [
        ("a", [1.0, 0.0, 0.0]),
        ("b", [0.9, 0.1, 0.0]),
        ("c", [0.5, 0.5, 0.0]),
        ("d", [0.0, 1.0, 0.0]),
        ("e", [-1.0, 0.0, 0.0]),
    ]:
        r.vset().vadd("myset", vec, name, quantization=QuantizationOptions.NOQUANT)

    result = r.vset().vsim("myset", input="a", count=2)
    assert len(result) == 2
    assert result[0] == b"a"
    assert result[1] == b"b"

    result_all = r.vset().vsim("myset", input="a", count=100)
    assert len(result_all) == 5
    assert result_all[0] == b"a"
    assert result_all[-1] == b"e"


def test_vcard_exact_count(r: redis.Redis):
    """Test vcard returns the precise element count after each modification."""
    r.vset().vadd("myset", [1.0, 0.0], "a")
    assert r.vset().vcard("myset") == 1

    r.vset().vadd("myset", [0.0, 1.0], "b")
    r.vset().vadd("myset", [-1.0, 0.0], "c")
    assert r.vset().vcard("myset") == 3

    r.vset().vrem("myset", "b")
    assert r.vset().vcard("myset") == 2


def test_vrem_exact(r: redis.Redis):
    """Test vrem removes exactly the targeted element and returns correct status codes."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b")
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "c")

    assert r.vset().vrem("myset", "b") == 1
    assert r.vset().vcard("myset") == 2
    assert r.vset().vemb("myset", "b") is None
    assert r.vset().vemb("myset", "a") is not None
    assert r.vset().vemb("myset", "c") is not None

    assert r.vset().vrem("myset", "b") == 0
    assert r.vset().vcard("myset") == 2

    assert r.vset().vrem("myset_nonexistent", "a") == 0


def test_vinfo_exact_fields(r: redis.Redis):
    """Test vinfo returns correct size, dim, uid, and quant-type for a known set."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b", quantization=QuantizationOptions.NOQUANT)

    info = r.vset().vinfo("myset")
    assert info[b"quant-type"] == b"f32"
    assert info[b"vector-dim"] == 3
    assert info[b"size"] == 2
    assert info[b"hnsw-max-node-uid"] == 2

    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "c", quantization=QuantizationOptions.NOQUANT)
    info = r.vset().vinfo("myset")
    assert info[b"size"] == 3
    assert info[b"hnsw-max-node-uid"] == 3


def test_vinfo_bin_quant_type(r: redis.Redis):
    """Test vinfo reports bin quantization type and correct dimension."""
    r.vset().vadd("myset", [1.0, 4.0, 0.0, -1.0], "a", quantization=QuantizationOptions.BIN)

    info = r.vset().vinfo("myset")
    assert info[b"quant-type"] == b"bin"
    assert info[b"vector-dim"] == 4
    assert info[b"size"] == 1


def test_vinfo_int8_quant_type(r: redis.Redis):
    """Test vinfo reports int8 as the default quantization type."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")

    info = r.vset().vinfo("myset")
    assert info[b"quant-type"] == b"int8"
    assert info[b"vector-dim"] == 3
    assert info[b"size"] == 1


def test_vrandmember_exact_pool(r: redis.Redis):
    """Test vrandmember always returns members from the exact set, with correct counts."""
    known = {"alpha", "beta", "gamma"}
    r.vset().vadd("myset", [1.0, 0.0], "alpha")
    r.vset().vadd("myset", [0.0, 1.0], "beta")
    r.vset().vadd("myset", [-1.0, 0.0], "gamma")

    single = r.vset().vrandmember("myset")
    assert single.decode() in known

    all_unique = r.vset().vrandmember("myset", count=3)
    assert len(all_unique) == 3
    assert {m.decode() for m in all_unique} == known

    more_than_set = r.vset().vrandmember("myset", count=10)
    assert len(more_than_set) == 3
    assert {m.decode() for m in more_than_set} == known

    with_reps = r.vset().vrandmember("myset", count=-5)
    assert len(with_reps) == 5
    assert all(m.decode() in known for m in with_reps)


def test_vlinks_valid_neighbors(r: redis.Redis):
    """Test vlinks returns only valid element names (no self-links, no unknown names)."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b")
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "c")

    valid = {b"a", b"b", b"c"}
    for name in [b"a", b"b", b"c"]:
        links = r.vset().vlinks("myset", name)
        assert links is not None
        for layer in links:
            assert isinstance(layer, list)
            for neighbor in layer:
                assert neighbor in valid
                assert neighbor != name

    links_with_scores = r.vset().vlinks("myset", b"b", with_scores=True)
    assert links_with_scores is not None
    for layer_dict in links_with_scores:
        assert isinstance(layer_dict, dict)
        for neighbor, score in layer_dict.items():
            assert neighbor in valid
            assert neighbor != b"b"
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0


def test_vcard_nonexistent_key(r: redis.Redis):
    """Test that vcard returns None (nil) for a key that does not exist."""
    assert r.vset().vcard("nonexistent") is None


def test_vadd_multiple_quant_types(r: redis.Redis):
    """Test that specifying two quantization flags in one VADD raises an error."""
    with pytest.raises(redis.ResponseError, match="multiple quantization"):
        r.execute_command("VADD", "myset", "VALUES", "3", "1.0", "0.0", "0.0", "a", "BIN", "Q8")


def test_vadd_values_insufficient_args(r: redis.Redis):
    """Test that VADD VALUES N raises when fewer than N floats follow."""
    with pytest.raises(redis.ResponseError):
        # Claims 5 values but only 2 are provided before the element name
        r.execute_command("VADD", "myset", "VALUES", "5", "1.0", "2.0", "a")


def test_vadd_unknown_syntax(r: redis.Redis):
    """Test that an unrecognised VADD keyword raises a syntax error."""
    with pytest.raises(redis.ResponseError, match="syntax error"):
        r.execute_command("VADD", "myset", "VALUES", "3", "1.0", "0.0", "0.0", "a", "BADPARAM")


def test_vemb_too_many_args(r: redis.Redis):
    """Test that VEMB with more than one optional arg raises an error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    with pytest.raises(redis.ResponseError, match="wrong number of arguments"):
        r.execute_command("VEMB", "myset", "a", "RAW", "EXTRA")


def test_vrange_too_many_args(r: redis.Redis):
    """Test that VRANGE with more than one extra arg (after min/max) raises an error."""
    r.vset().vadd("myset", [1.0, 2.0], "a")
    with pytest.raises(redis.ResponseError):
        r.execute_command("VRANGE", "myset", "-", "+", "5", "EXTRA")


def test_vsim_duplicate_ele(r: redis.Redis):
    """Test that specifying ELE twice in VSIM raises an error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b")
    with pytest.raises(redis.ResponseError):
        r.execute_command("VSIM", "myset", "ELE", "a", "ELE", "b")


def test_vsim_duplicate_values(r: redis.Redis):
    """Test that specifying VALUES twice in VSIM raises an error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    with pytest.raises(redis.ResponseError):
        r.execute_command("VSIM", "myset", "VALUES", "3", "1.0", "0.0", "0.0", "VALUES", "3", "1.0", "0.0", "0.0")


def test_vsim_values_insufficient_args(r: redis.Redis):
    """Test that VSIM VALUES N raises when fewer than N floats follow."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    with pytest.raises(redis.ResponseError):
        r.execute_command("VSIM", "myset", "VALUES", "5", "1.0", "2.0")


def test_vsim_epsilon(r: redis.Redis):
    """Test that VSIM EPSILON filters out elements below the similarity threshold."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "same", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "orthogonal", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "opposite", quantization=QuantizationOptions.NOQUANT)

    # epsilon=0.1: keep score >= 0.9; only "same" (score=1.0) qualifies
    result = r.execute_command("VSIM", "myset", "ELE", "same", "EPSILON", "0.1")
    assert result == [b"same"]

    # epsilon=0.6: keep score >= 0.4; "same" (1.0) and "orthogonal" (0.5) qualify
    result = r.execute_command("VSIM", "myset", "ELE", "same", "EPSILON", "0.6")
    assert set(result) == {b"same", b"orthogonal"}


def test_vsim_truth_nothread(r: redis.Redis):
    """Test that VSIM with TRUTH and NOTHREAD flags returns the same results."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a", quantization=QuantizationOptions.NOQUANT)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b", quantization=QuantizationOptions.NOQUANT)

    base = r.execute_command("VSIM", "myset", "ELE", "a")
    with_truth = r.execute_command("VSIM", "myset", "ELE", "a", "TRUTH")
    with_nothread = r.execute_command("VSIM", "myset", "ELE", "a", "NOTHREAD")

    assert set(base) == set(with_truth) == set(with_nothread)


def test_vsim_no_vector_specified(r: redis.Redis):
    """Test that VSIM without ELE/FP32/VALUES raises an error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    with pytest.raises(redis.ResponseError):
        r.execute_command("VSIM", "myset", "WITHSCORES")


def test_vsim_syntax_error(r: redis.Redis):
    """Test that an unrecognised VSIM keyword raises a syntax error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a")
    with pytest.raises(redis.ResponseError, match="syntax"):
        r.execute_command("VSIM", "myset", "ELE", "a", "BADPARAM")


def test_vsim_invalid_filter_expression(r: redis.Redis):
    """Test that an unparseable FILTER expression raises an error."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a", attributes={"x": 1})
    with pytest.raises(redis.ResponseError):
        r.execute_command("VSIM", "myset", "ELE", "a", "FILTER", "!!!invalid!!!")


def test_vsim_filter_excludes_no_attr_elements(r: redis.Redis):
    """Test that VSIM FILTER skips elements that have no attributes (accept_filter → False)."""
    r.vset().vadd("myset", [1.0, 0.0], "has_attr", attributes={"score": 100})
    r.vset().vadd("myset", [0.9, 0.1], "low_attr", attributes={"score": 1})
    r.vset().vadd("myset", [0.8, 0.2], "no_attr")

    # Only "has_attr" has score > 50; "no_attr" is excluded because it has no attributes
    result = r.vset().vsim("myset", input="has_attr", filter=".score > 50", count=3)
    assert b"has_attr" in result
    assert b"no_attr" not in result
    assert b"low_attr" not in result


def test_vsim_zero_norm_vector(r: redis.Redis):
    """Test that similarity with a zero-norm vector returns 0.0."""
    r.execute_command("VADD", "myset", "VALUES", "3", "0.0", "0.0", "0.0", "zero")
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "unit")

    result = r.vset().vsim("myset", input="zero", with_scores=True, count=2)
    assert result[b"zero"] == pytest.approx(0.0, abs=0.001)
    assert result[b"unit"] == pytest.approx(0.0, abs=0.001)


def test_vadd_numlinks_one(r: redis.Redis):
    """Test vadd with numlinks=1 (exercises _compute_level branch where m <= 1)."""
    r.vset().vadd("myset", [1.0, 0.0, 0.0], "a", numlinks=1)
    r.vset().vadd("myset", [0.0, 1.0, 0.0], "b", numlinks=1)
    r.vset().vadd("myset", [-1.0, 0.0, 0.0], "c", numlinks=1)

    assert r.vset().vcard("myset") == 3
    info = r.vset().vinfo("myset")
    assert info[b"size"] == 3


@pytest.mark.parametrize(
    "cmd_args",
    [
        ("VCARD", "not_a_vset"),
        ("VDIM", "not_a_vset"),
        ("VGETATTR", "not_a_vset", "member"),
        ("VSETATTR", "not_a_vset", "member", "{}"),
        ("VEMB", "not_a_vset", "member"),
        ("VREM", "not_a_vset", "member"),
        ("VRANGE", "not_a_vset", "-", "+"),
        ("VSIM", "not_a_vset", "ELE", "member"),
        ("VINFO", "not_a_vset"),
        ("VLINKS", "not_a_vset", "member"),
    ],
)
def test_wrongtype_on_string_key(r: redis.Redis, cmd_args):
    """All vset commands raise WRONGTYPE when the key holds a string."""
    r.set("not_a_vset", "some_value")
    with pytest.raises(redis.ResponseError) as excinfo:
        r.execute_command(*cmd_args)
    assert "WRONGTYPE" in excinfo.value.args[0]
