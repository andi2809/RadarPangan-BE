# Radar Pangan — perintah operasional (jalankan dari root repo)
PY ?= .venv/bin/python
TANGGAL ?= $(shell date +%F)

.PHONY: help test integrity fetch rekonsiliasi sp2kp-fetch sp2kp-import gabung harga-utama backtest exports deploy semua

help:
	@echo "make test          # seluruh uji (pytest)"
	@echo "make integrity     # uji integritas data saja"
	@echo "make fetch         # tarik PIHPS hari ini (START/END bisa di-override)"
	@echo "make rekonsiliasi  # bandingkan PIHPS vs SP2KP (TANGGAL=YYYY-MM-DD)"
	@echo "make sp2kp-fetch START=2026-10-19 END=2026-10-26  # tarik SP2KP 27 kab/kota"
	@echo "make sp2kp-import BERKAS=ekspor.csv|xlsx  # impor ekspor SP2KP (CSV/XLSX)"
	@echo "make harga-utama   # satu tabel untuk FE (PIHPS prioritas, SP2KP tambalan)"
	@echo "make gabung        # gabungkan PIHPS+SP2KP jadi data/derived/gabungan_harga.csv"
	@echo "make backtest      # backtest ambang EWS"
	@echo "make exports       # regenerasi openapi.json + fixtures"
	@echo "make deploy        # deploy ke Vercel produksi"
	@echo "make semua         # test + rekonsiliasi + backtest + exports"

test:
	$(PY) -m pytest -q

integrity:
	$(PY) -m pytest tests/test_data_integrity.py -q

START ?= $(TANGGAL)
END ?= $(TANGGAL)
fetch:
	$(PY) pipeline/pihps_fetch.py --start $(START) --end $(END)

rekonsiliasi:
	$(PY) pipeline/rekonsiliasi.py --tanggal $(TANGGAL)

sp2kp-fetch:
	$(PY) pipeline/sp2kp_fetch.py --start $(START) --end $(END)

sp2kp-import:
	$(PY) pipeline/sp2kp_import.py --berkas $(BERKAS)

harga-utama:
	$(PY) pipeline/harga_utama.py

gabung:
	$(PY) pipeline/gabung_ekspor.py

backtest:
	$(PY) pipeline/backtest.py

exports:
	PYTHONPATH=. $(PY) scripts/export_openapi.py

deploy:
	npx --yes vercel@latest --prod --yes

semua: test rekonsiliasi backtest exports
