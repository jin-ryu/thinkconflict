#!/bin/bash
# LaTeX Workshop 및 PDF 컴파일을 위한 패키지 설치 스크립트
# Ubuntu/Debian 기반 시스템용

set -e

echo "=== LaTeX Workshop 필수 패키지 설치 ==="

# 기본 TeX Live 설치 (pdflatex, bibtex 포함)
sudo apt-get update
sudo apt-get install -y texlive-latex-base

# 추천 패키지 (대부분의 논문 작성에 필요)
sudo apt-get install -y texlive-latex-recommended

# 추가 패키지 (tabularx, colortbl, float 등 포함)
sudo apt-get install -y texlive-latex-extra

# 폰트 패키지
sudo apt-get install -y texlive-fonts-recommended
sudo apt-get install -y texlive-fonts-extra

# latexmk (LaTeX Workshop 기본 빌드 도구)
sudo apt-get install -y latexmk

# bibtex 관련 (참고문헌)
sudo apt-get install -y texlive-bibtex-extra

# 한글 지원 (main_ko.tex의 kotex 패키지에 필요)
sudo apt-get install -y texlive-lang-korean

# 과학/수학 기호 패키지
sudo apt-get install -y texlive-science

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "설치된 도구 버전:"
pdflatex --version | head -1
latexmk --version | head -1
bibtex --version | head -1

echo ""
echo "LaTeX Workshop 사용 준비 완료!"
