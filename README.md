# Monitor Mirror PiP

App leve para Windows que espelha um monitor secundário (ex.: Virtual Display / VDD) em uma janela **PiP** no monitor primário.

Ideal para acompanhar um display virtual (Sunshine, Moonlight, apps em segundo monitor) sem alternar de tela.

## Recursos

- Ícone na **bandeja do sistema**
- **Clique esquerdo**: mostrar / ocultar PiP
- **Clique direito**: escolher o monitor fonte
- Janela **borderless** (sem barra de título), arrastável
- Sempre no **monitor primário**
- Blit via **GDI StretchBlt** (CPU baixa com PiP ativo)
- **Idle** ao ocultar: para o loop de frames (~0% CPU)
- Task Manager: **Monitor Mirror PiP** / `MonitorMirrorPiP.exe`
- Opcional: inicia com o Windows

## Requisitos

- Windows 10/11
- Dois ou mais monitores ativos (físico e/ou virtual)
- Python 3.10+ só se for rodar/buildar a partir do código-fonte

## Instalação rápida (release)

1. Baixe os assets na [página de Releases](https://github.com/canetex/monitor-mirror-pip/releases).
2. Preferência: rode o **`MonitorMirrorPiP.exe`** standalone (não precisa de Python).
3. Ou extraia `MonitorMirrorPiP-Setup.zip` e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

O instalador copia o exe para `%LOCALAPPDATA%\MonitorMirror` e cria atalhos (Desktop, Menu Iniciar, Startup).

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

### Dependências (dev)

- `Pillow` — ícone da bandeja
- `pystray` — bandeja

## Arquitetura

```
Bandeja (pystray)
    │ clique direito → seleciona monitor fonte (não-primário)
    │ clique esquerdo → show/hide (idle sem blit)
    ▼
PipWindow (tkinter, overrideredirect)
    │ sempre no monitor primário
    ▼
GDI StretchBlt (desktop DC → HWND do PiP)
```

## Build do release

```powershell
.\.venv\Scripts\pip install pyinstaller
python -c "from mirror import make_tray_icon; make_tray_icon(256).save('monitor-mirror.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(256,256)])"
.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --noconsole `
  --name MonitorMirrorPiP `
  --version-file version_info.txt `
  --icon monitor-mirror.ico `
  --hidden-import=pystray._win32 `
  --collect-all pystray `
  mirror.py
```

O binário sai em `dist\MonitorMirrorPiP.exe` (FileDescription = *Monitor Mirror PiP*).

## Licença

Uso pessoal / lab. Sem garantia.
