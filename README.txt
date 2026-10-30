LANGAN EXPLORER DESKTOP - WINDOWS BUILD KIT

This is a Windows build kit, not a precompiled EXE. PyInstaller must bundle Windows binaries on Windows.

FEATURES
- Local SmolLM2 360M Instruct Q5_0 model bundled into the one-file EXE.
- Desktop problem-analysis interface.
- Password-protected Python logic-engine editor.
- Editable evidence-source URL list.
- Local AI inference after build; evidence fetching requires internet.

REQUIREMENTS
- Windows 10/11 64-bit.
- Python 3.11 64-bit from python.org; enable Add Python to PATH.
- Internet for first model download and package installation.
- At least 1 GB free disk space recommended.

BUILD
1. Extract the ZIP to a normal folder (for example Desktop\Langan_Explorer_Desktop).
2. Double-click DOWNLOAD_MODEL.bat (downloads about 268 MB).
3. Double-click BUILD_EXE.bat and wait for completion.
4. EXE output: dist\LanganExplorer.exe.
5. Run it. On first launch create your administrator password.
6. Use LOGIC ENGINE > Unlock editor to edit Python code.
7. Use EVIDENCE SOURCES to change page URLs used for research.

MODEL
SmolLM2-360M-Instruct Q5_0 GGUF, from the Unsloth Hugging Face repository.
The model is bundled into the one-file EXE. First launch can take time while the EXE extracts its bundled model.

SECURITY
The password is stored as a salted PBKDF2 hash in data/settings.json.
This protects the editor interface only; it is not strong protection against a technically skilled person with full access to the computer.
Python code saved in the editor can execute with your Windows account permissions. Only use code you trust.
Backups are created when logic code is saved.

LIMITATIONS
This is an experimental prototype, not a validated high-accuracy reasoning system.
SmolLM2 360M can make mistakes. A small language model cannot guarantee sound reasoning.
The evidence feature fetches configured page URLs; it does not crawl entire sites or verify whether a claim is true.
The default logic engine is a starter function. You must add your own logic code to make it perform custom logical operations.
