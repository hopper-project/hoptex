rm eqs.tsv
rm tex_to_eqs.tsv
rm eqs_to_tex.tsv
touch eqs.tsv
touch tex_to_eqs.tsv
touch eqs_to_tex.tsv
#python3 enumerate_eqs.py --tsv eqs.tsv --tex_eqs tex_to_eqs.tsv --eqs_tex eqs_to_tex.tsv ./processed_articles/physics/ eqs.tsv
#python3 enumerate_inline_eqs.py --tsv eqs.tsv --tex_eqs tex_to_eqs.tsv --eqs_tex eqs_to_tex.tsv ./processed_articles/physics/ eqs.tsv
#python3 enumerate_docs.py ./processed_articles/physics/ eqs.tsv --outpath enumerate_docs
#python3 enumerate_docs.py ./enumerate_docs eqs.tsv --outpath enumerate_docs --inline
#python3 striplatex.py processed_articles/physics/ striplatex
python3 enumerate.py --tsv eqs.tsv --tex_eqs tex_to_eqs.tsv --eqs_tex eqs_to_tex.tsv --docpath enumerate_docs ./1000articles/ eqs.tsv
python3 process_tsv.py --tsv_file eqs.tsv --tex_list sep_articles_list/test.txt --mml_dir MML_DIR --json_dir JSON_DIR ./1000articles XHTML_DIR