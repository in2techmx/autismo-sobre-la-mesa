# 🤖 Bot de Telegram — «El Autismo Sobre La Mesa»

Servicio conversacional en Telegram para **acompañar a familias, educadores y terapeutas** en el seguimiento diario de la **Bitácora de Alimentación** y la resolución de dudas sobre selectividad alimentaria e integración sensorial en niños con Trastorno del Espectro Autista (TEA).

Basado íntegramente en el Trabajo de Fin de Máster (TFM) de la **Mtra. Maria Cindy Morales Alarcón**:
> *«Selectividad alimentaria en niños con Trastorno del Espectro Autista en edad escolar de Educación Primaria: revisión narrativa como fundamento para la guía educativa "El Autismo Sobre La Mesa"»* (Máster Universitario en Nutrición y Alimentación, 2025-2026).

---

## ✨ ¿Qué hace este servicio?

1. **Seguimiento Automático de Bitácora por Texto Libre:**
   Escríbele con tus propias palabras (ej. *"Hoy Mía tocó el brócoli al vapor con el dedo y estuvo tranquila"*). El motor detecta automáticamente:
   - **Alimento** (*Brócoli*)
   - **Escalón en la Escalera Sensorial** (*Toleró presencia / Olió / Tocó / Acercó a la boca / Probó / Comió / Rechazó*)
   - **Textura / Presentación** (*Al vapor, crujiente, puré, crudo...*)
   - **Estado Emocional / Regulación** (*En calma, curioso, ansioso, sobrecargado*)
   - Lo guarda en una base de datos local **SQLite** privada por usuario.

2. **Asesoría Basada en Evidencia Científica (Gemini AI + Motor Clínico TFM):**
   Responde dudas sobre selectividad alimentaria, rechazo a texturas mixtas, técnica del *Alimento Puente (Food Chaining)*, mito del peso corporal, factores gastrointestinales y regulación sensorial previa a las comidas.

3. **Exportación Instantánea a Excel / CSV (`/exportar`):**
   Genera en un clic la bitácora completa en formato `.csv` (codificado con UTF-8 BOM para abrir directamente en Microsoft Excel con acentos perfectos) lista para compartir con el **Terapeuta Ocupacional, Logopeda o Nutricionista Pediátrico**.

---

## 🚀 Cómo ponerlo en marcha en 3 pasos

### 1. Crear el Bot en Telegram (1 minuto)
1. Abre Telegram y busca a **[@BotFather](https://t.me/BotFather)**.
2. Envíale el comando `/newbot`.
3. Ponle un nombre (ej. `El Autismo Sobre La Mesa`) y un usuario terminado en `bot` (ej. `AutismoSobreLaMesaBot`).
4. Copia el **Token** que te entrega.

### 2. Instalar dependencias
```powershell
cd telegram_bot
pip install -r requirements.txt
```

### 3. Configurar tus credenciales y arrancar
En PowerShell:
```powershell
$env:TELEGRAM_BOT_TOKEN="PEGA_AQUI_TU_TOKEN_DE_BOTFATHER"
# Opcional: Para respuestas generativas avanzadas con Google Gemini
$env:GEMINI_API_KEY="PEGA_AQUI_TU_API_KEY_DE_GEMINI"

python bot.py
```

---

## 🧪 Ejecutar Pruebas Automatizadas (Gate 1)
```powershell
python -m unittest discover -s telegram_bot/tests -v
```
