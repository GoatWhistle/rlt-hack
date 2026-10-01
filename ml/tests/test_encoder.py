import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from rlt_ml.encoder import contrastive_loss, contrastive_masks
from rlt_ml.text_encoder import format_text, pool


def test_known_positive_supplier_is_never_a_negative():
    rows = [
        {"query_text": "q1", "supplier_inn": "a", "known_positive_inns": ["a", "b"], "sample_weight": 1},
        {"query_text": "q2", "supplier_inn": "b", "known_positive_inns": ["b"], "sample_weight": 1},
        {"query_text": "q1", "supplier_inn": "c", "known_positive_inns": ["a", "b", "c"], "sample_weight": 1},
    ]
    positive, allowed = contrastive_masks(rows)
    assert positive[0] == [True, False, True]
    assert allowed[0] == [True, False, True]
    vectors = torch.eye(3, requires_grad=True)
    loss, useful = contrastive_loss(vectors, vectors, rows, 0.05)
    assert useful and torch.isfinite(loss)
    loss.backward()
    assert torch.isfinite(vectors.grad).all()


def test_qwen_pooling_handles_left_and_right_padding():
    values = torch.tensor([[[1., 0.], [0., 1.], [1., 1.]], [[1., 0.], [0., 1.], [1., 1.]]])
    mask = torch.tensor([[0, 1, 1], [1, 1, 0]])
    result = pool(values, mask, "qwen")
    assert torch.allclose(result[0], torch.tensor([2**-0.5, 2**-0.5]))
    assert torch.allclose(result[1], torch.tensor([0., 1.]))
    assert format_text("текст", "qwen", True, "Find suppliers") == "Instruct: Find suppliers\nQuery: текст"
    assert format_text("текст", "e5", False, "") == "passage: текст"


def test_no_negative_batch_does_not_make_invalid_loss():
    rows = [{"query_text": "q", "supplier_inn": "a", "known_positive_inns": ["a"], "sample_weight": 1}]
    vectors = torch.tensor([[1., 0.]], requires_grad=True)
    loss, useful = contrastive_loss(vectors, vectors, rows, 0.05)
    assert loss == 0 and not useful
