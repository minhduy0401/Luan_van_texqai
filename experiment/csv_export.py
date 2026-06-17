# experiment/csv_export.py – Xuất CSV thí nghiệm (ghi tăng dần + bản Excel)
import csv
from pathlib import Path

EXP1_FIELDNAMES = [
    'model', 'model_short', 'pdf', 'bloom_level', 'bloom_short', 'source_chapter',
    'section_info', 'bleu1_ans_chapter', 'bleu2_ans_chapter', 'bleu4_ans_chapter',
    'best_bleu_chapter', 'best_bleu_score', 'is_correct', 'bleu4_ans_section',
    'bleu4_q_chapter', 'answer_words', 'question_words', 'chapter_words',
    'section_words', 'process_time_s', 'total_points', 'question', 'answer',
]

EXP2_FIELDNAMES_BASE = [
    'idx', 'pdf', 'bloom_level', 'bloom_short', 'sys_bloom_int', 'chapter',
    'n_agree', 'is_2llm', 'is_3llm', 'process_time_s', 'question', 'answer',
]


def exp2_fieldnames(evaluator_models: list[str]) -> list[str]:
    eval_shorts = [m.split('/')[-1] for m in evaluator_models]
    names = list(EXP2_FIELDNAMES_BASE[:6])
    for j, _ in enumerate(eval_shorts):
        names += [f'bloom_pred_{j}', f'bloom_pred_name_{j}', f'agree_{j}', f'eval_time_{j}']
    names += list(EXP2_FIELDNAMES_BASE[6:])
    return names


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8-sig', errors='replace') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
            extrasaction='ignore',
        )
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def write_csv_pair(base_path: Path, rows: list[dict], fieldnames: list[str]) -> tuple[Path, Path]:
    """Ghi exp*_raw_<ts>.csv và bản _excel.csv (cùng nội dung, tương thích Excel)."""
    write_csv(base_path, rows, fieldnames)
    excel_path = base_path.with_name(base_path.stem + '_excel.csv')
    write_csv(excel_path, rows, fieldnames)
    return base_path, excel_path
