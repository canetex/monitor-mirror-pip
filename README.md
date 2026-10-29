# Monitor Mirror PiP

App leve para Windows que espelha um monitor secundário (ex.: Virtual Display / VDD) em uma janela **PiP** no monitor primário.

Ideal para acompanhar um display virtual (Sunshine, Moonlight, apps em segundo monitor) sem alternar de tela.

## Recursos

- Ícone na **bandeja do sistema**
- **Clique esquerdo**: mostrar / ocultar PiP
- **Clique direito**: escolher o monitor fonte
- Janela **borderless** (sem barra de título), arrastável
- Sempre no **monitor primário**
- Processo aparece no Task Manager como `MonitorMirrorPiP.exe`
- Opcional: inicia com o Windows

## Requisitos

- Windows 10/11
- Python 3.10+ (apenas para instalação via script)
- Dois ou mais monitores ativos (físico e/ou virtual)

## Instalação rápida (release)

1. Baixe o asset `MonitorMirrorPiP-Setup.zip` na [página de Releases](https://github.com/canetex/monitor-mirror-pip/releases).
2. Extraia e execute `install.ps1` no PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

O instalador:

- copia o app para `%LOCALAPPDATA%\MonitorMirror`
- cria venv e instala dependências
- gera `MonitorMirrorPiP.exe` (nome visível no Task Manager)
- cria atalhos no Desktop, Menu Iniciar e **Startup**

### Executável standalone

Na mesma release há `MonitorMirrorPiP.exe` (PyInstaller). Basta baixar e executar — não precisa instalar Python. O ícone fica na bandeja.

## Uso

| Ação | Resultado |
|------|-----------|
| Clique esquerdo na bandeja | Show / hide do PiP |
| Clique direito → monitor | Define a fonte capturada |
| Arrastar o PiP | Move a janela no primário |
| ESC (com PiP focado) | Oculta o PiP |
| Sair (menu) | Encerra o app |

## Desenvolvimento

```powershell
cd monitor-mirror
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python mirror.py
```

Testes:

```powershell
python -m pytest tests -q
```

### Dependências

- `dxcam` — captura DXGI (GPU)
- `Pillow` — frames / ícone
- `pystray` — bandeja

## Arquitetura

```
Bandeja (pystray)
    │ clique direito → seleciona monitor fonte (não-primário)
    │ clique esquerdo → show/hide
    ▼
PipWindow (tkinter, overrideredirect)
    │ sempre no monitor primário
    │ captura via dxcam (output_idx da fonte)
    ▼
Frame RGB → resize letterbox → canvas
```

## Build do release

```powershell
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --noconsole `
  --name MonitorMirrorPiP `
  --hidden-import=pystray._win32 `
  mirror.py
```

O binário sai em `dist\MonitorMirrorPiP.exe`.

## Licença

Uso pessoal / lab. Sem garantia.
