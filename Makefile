# Radar Pangan — perintah operasional (jalankan dari root repo)
PY ?= .venv/bin/python
TANGGAL ?= $(shell date +%F)

.PHONY: help test integrity fetch rekonsiliasi sp2kp-fetch sp2kp-import gabung bapanas paket pita harga-utama backtest exports deploy semua

help:
	@echo "make test          # seluruh uji (pytest)"
	@echo "make integrity     # uji integritas data saja"
	@echo "make bapanas       # impor Excel Bapanas -> data/paket/bapanas.csv.gz"
	@echo "make ann           # latih 162 model ANN Perceptron (5-16-1) -> data/derived/bobot_ann_h7.json"
	@echo "make paket         # gabung+gzip arsip untuk bundel serverless (0,4 MB)"
	@echo "make exports       # regenerasi openapi.json + fixtures"
	@echo "make deploy        # deploy ke Vercel produksi"
	@echo "make semua         # test + integritas + bapanas + ann + exports"

test:
	$(PY) -m pytest -q

integrity:
	$(PY) -m pytest tests/test_data_integrity.py -q

START ?= $(TANGGAL)
END ?= $(TANGGAL)




integritas:
	$(PY) pipeline/integritas_bapanas.py --ringkas 2>/dev/null || $(PY) pipeline/integritas_bapanas.py

bapanas:
	$(PY) pipeline/bapanas_import.py

ann:
	$(PY) pipeline/prediksi_ann_h7.py

paket:
	$(PY) pipeline/paket_kompres.py





exports:
	PYTHONPATH=. $(PY) scripts/export_openapi.py

deploy:
	npx --yes vercel@latest --prod --yes

semua: test integritas bapanas disparitas exports
