# Use LuaLaTeX + biber
$pdf_mode = 4;
$lualatex = 'lualatex --shell-escape --interaction=nonstopmode --synctex=1 %O %S';
$biber    = 'biber %O %B';
$clean_ext = 'synctex.gz aux log out toc lof lot fls fdb_latexmk bbl bcf blg run.xml';
