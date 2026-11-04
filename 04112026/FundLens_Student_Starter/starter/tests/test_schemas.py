from fundlens.schemas import AnswerOutput, Citation


def test_answer_output_contract():
    a = AnswerOutput(answer="1.89% [DATA-FUND-MASTER §F01/A-Acc-USD]", route="fact",
                     citations=[Citation(doc_id="DATA-FUND-MASTER", section="F01/A-Acc-USD")])
    assert a.review_status == "n/a" and not a.refused
