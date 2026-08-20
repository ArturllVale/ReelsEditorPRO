# Auditoria ReelsEditorPRO

Auditoria da base de código focada nos itens solicitados, avaliando a implementação real existente:

**1. ciclo de vida de ProcessPoolExecutor**
PASS

**2. ciclo de vida de multiprocessing.Manager**
PASS

**3. detecção de GPU**
FAIL
- **arquivo:** `ui/main_window.py` (e `domain/models.py`)
- **linha aproximada:** 199 (`ui/main_window.py`)
- **problema:** Não há qualquer código de detecção real das placas de vídeo (como ler flags do SO ou `ffmpeg -hwaccels`). As opções de GPU "h264_nvenc" e "h264_amf" são strings inseridas estaticamente no ComboBox.
- **impacto:** Qualquer usuário, mesmo em computadores sem GPU NVIDIA ou AMD, pode selecionar o respectivo codec na UI. Isso resultará em erro fatal de subprocesso no exato momento em que a renderização iniciar.
- **recomendação:** Implementar rotina de inicialização para verificar programaticamente a existência de GPUs e drivers compatíveis no sistema, preenchendo a interface apenas com as opções suportadas pelo hardware local.

**4. concorrência CPU/GPU**
PASS

**5. cancelamento real do FFmpeg**
PASS

**6. stderr do FFmpeg**
FAIL
- **arquivo:** `core/video_processor.py` (classe `ProcessRunner`)
- **linha aproximada:** 237 a 250
- **problema:** O laço `for line in process.stderr:` exaure o buffer do stream de erro ao procurar o progresso via regex. Na verificação de erro subsequente (`if process.returncode != 0:`), o script tenta ler a saída com `process.stderr.read()`, o que retornará uma string vazia porque o cursor já está no fim do arquivo (EOF).
- **impacto:** Exceções originadas pelo FFmpeg irão gerar a mensagem "FFmpeg error: " vazia, omitindo a real causa da falha. Omitir a causa raiz cria um ponto cego no sistema para debugging.
- **recomendação:** Acumular em memória as últimas linhas lidas no `for` (ex: usando uma lista ou string), e, caso ocorra erro (returncode != 0), utilizá-las para estruturar a string completa de exceção devolvida.

**7. FFprobe**
FAIL
- **arquivo:** `core/video_processor.py` (classe `MetadataReader`)
- **linha aproximada:** 16 (comando global) e 86 (fallback mágico)
- **problema:** Primeiro tenta executar `ffprobe` confiando que esteja no `PATH` global, ao invés de buscar a versão embarcada (como faz com `ffmpeg_exe`). Além disso, na leitura de metadados via regex do FFmpeg (fallback `_get_info_fallback`), caso o regex não encontre a resolução de vídeo (ex: mídia corrompida), o sistema engole a falha e atribui os valores arbitrários e mágicos de `1920x1080` (linha 86).
- **impacto:** Falhará desnecessariamente em sistemas onde `ffprobe` não é global. O pior é que violará as instruções do sistema, silenciando problemas de leitura e exportando vídeos corrompidos num formato errado de `1920x1080` de forma mascarada.
- **recomendação:** Usar `imageio_ffmpeg` (ou similar) para determinar o binário do `ffprobe` e invocá-lo de maneira exata. Além disso, remover o bloco `meta.width = 1920; meta.height = 1080` do script e disparar explicitamente uma exceção (como `ValueError`) em vez de silenciar falhas de leitura de dimensão.

**8. preview debounce**
PASS

**9. Project como objeto interno**
PASS

**10. processamento de múltiplos vídeos**
PASS
