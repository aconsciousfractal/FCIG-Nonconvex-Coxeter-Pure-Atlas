# Paper source

The title-named PDF `The_Nonconvex_A3_Coxeter-Chamber_Atlas.pdf` is built from a fresh staged copy by the
release-candidate exporter.  Rebuild from this directory with:

```bash
job=The_Nonconvex_A3_Coxeter-Chamber_Atlas
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
bibtex "$job"
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
```

The two files under `figures/` derived from the earlier T2 package are
identified in `../THIRD_PARTY_NOTICES.md` and remain CC BY 4.0.
