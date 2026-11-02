@echo off
pip install pyinstaller
pyinstaller --noconsole --onefile --uac-admin --name "StorageOptimizer" storage_optimizer.py
echo Build Selesai. Cek folder dist.
pause