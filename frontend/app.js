document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // 1. PINNED SCROLL GATE (OPENING & CLOSING WITH WOODEN SPINDLES)
    // ============================================================
    let lenisInstance = null;

    function initScrollExperience() {
        try {
            if (typeof gsap === "undefined") return;
            if (typeof ScrollTrigger !== "undefined") {
                gsap.registerPlugin(ScrollTrigger);
            }

            // 1.1 Lenis Smooth Scroll Engine
            if (typeof Lenis !== "undefined") {
                lenisInstance = new Lenis({
                    duration: 1.4,
                    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
                    smoothWheel: true
                });

                if (typeof ScrollTrigger !== "undefined") {
                    lenisInstance.on("scroll", ScrollTrigger.update);
                    gsap.ticker.add((time) => { lenisInstance.raf(time * 1000); });
                    gsap.ticker.lagSmoothing(0);
                }
            }

            // 1.2 GSAP ScrollTrigger: Pinned Unrolling Scroll Gate
            const scrollHero    = document.getElementById("scroll-unroll-hero");
            const parchmentGate = document.getElementById("parchment-gate");
            const topSpindle    = document.getElementById("top-spindle");
            const bottomSpindle = document.getElementById("bottom-spindle");
            const heroPrompt    = document.getElementById("hero-scroll-cta");

            if (scrollHero && parchmentGate && topSpindle && bottomSpindle && typeof ScrollTrigger !== "undefined") {
                const unrollTl = gsap.timeline({
                    scrollTrigger: {
                        trigger: scrollHero,
                        start: "top top",
                        end: "+=130%",
                        scrub: 0.8,
                        pin: true,
                        anticipatePin: 1
                    }
                });

                unrollTl.to(topSpindle, {
                    y: -60,
                    scale: 0.98,
                    ease: "power1.inOut"
                }, 0);

                unrollTl.to(bottomSpindle, {
                    y: 70,
                    scale: 1.02,
                    ease: "power1.inOut"
                }, 0);

                unrollTl.to(parchmentGate, {
                    height: "82vh",
                    ease: "power1.inOut"
                }, 0);

                const layers = [
                    { layer: "1", yPercent: 45 },
                    { layer: "2", yPercent: 30 },
                    { layer: "3", yPercent: -15 },
                    { layer: "4", yPercent: -40 }
                ];
                layers.forEach((layerObj) => {
                    const els = parchmentGate.querySelectorAll(`[data-parallax-layer="${layerObj.layer}"]`);
                    if (els.length > 0) {
                        unrollTl.to(els, { yPercent: layerObj.yPercent, ease: "none" }, 0);
                    }
                });

                if (heroPrompt) {
                    unrollTl.to(heroPrompt, { opacity: 0, y: 25, ease: "power1.out" }, 0.05);
                }
            }

        } catch (err) {
            console.warn("Scroll experience notice:", err);
        }
    }
    initScrollExperience();

    // Smooth scroll down to the Voice Oracle Chamber
    function scrollToOracleChamber() {
        const target = document.getElementById("main-app") || document.querySelector(".voice-sanctuary-stage");
        if (!target) return;

        if (lenisInstance) {
            lenisInstance.scrollTo(target, {
                offset: -20,
                duration: 1.6,
                easing: (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
            });
        } else {
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    const heroMicBtn = document.getElementById("hero-mic-btn");
    if (heroMicBtn) {
        heroMicBtn.addEventListener("click", (e) => {
            e.preventDefault();
            scrollToOracleChamber();
        });
    }

    const heroScrollCta = document.getElementById("hero-scroll-cta");
    if (heroScrollCta) {
        heroScrollCta.addEventListener("click", (e) => {
            e.preventDefault();
            scrollToOracleChamber();
        });
    }


    // ============================================================
    // 2. TOAST NOTIFICATION SYSTEM
    // ============================================================
    const Toast = {
        _container: document.getElementById("toast-container"),

        _create(type, title, description) {
            if (!this._container) return;
            const toast = document.createElement("div");
            toast.className = `toast toast--${type}`;
            toast.innerHTML = `
                <div class="toast__title">${title}</div>
                ${description ? `<div class="toast__description">${description}</div>` : ""}
                <button class="toast__close" aria-label="Dismiss">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2.5" stroke-linecap="round">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            `;
            this._container.appendChild(toast);

            requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("show")));

            const timer = setTimeout(() => this._dismiss(toast), 4500);
            toast.querySelector(".toast__close").addEventListener("click", () => {
                clearTimeout(timer);
                this._dismiss(toast);
            });
        },

        _dismiss(toast) {
            toast.classList.remove("show");
            toast.classList.add("hide");
            setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 400);
        },

        success(title, desc)  { this._create("success", title, desc); },
        error(title, desc)    { this._create("error",   title, desc); },
        info(title, desc)     { this._create("info",    title, desc); },
        warning(title, desc)  { this._create("warning", title, desc); }
    };


    // ============================================================
    // 3. CLEAN LOADER
    // ============================================================
    const Loader = {
        _overlay: document.getElementById("loader-overlay"),
        _textEl:  document.getElementById("loader-text"),

        show(message = "Consulting the Knowledge Scroll…") {
            if (this._textEl) this._textEl.textContent = message;
            this._overlay?.classList.remove("hidden");
        },
        hide() {
            this._overlay?.classList.add("hidden");
        }
    };


    // ============================================================
    // 4. ARTISTIC AI SOUND INSTALLATION (OCEAN RIPPLES & SAND WAVES)
    // ============================================================
    const VoiceDictator = (() => {
        const canvas = document.getElementById("voice-canvas");
        const sphereWrapper = document.getElementById("mic-btn");

        let gl = null, prog = null, uniforms = {};
        let animId = null;
        let amplitude = 0.04, targetAmplitude = 0.04;
        let currentState = "idle"; // 'idle', 'listening', 'processing', 'speaking'

        const VERT = `
            attribute vec2 aPosition;
            void main() { gl_Position = vec4(aPosition, 0.0, 1.0); }
        `;

        const FRAG = `
            precision highp float;
            uniform float uTime;
            uniform float uAmplitude;
            uniform vec2  uResolution;

            float bayerDither(vec2 coord) {
                vec2 p = floor(mod(coord, 8.0));
                float x = p.x; float y = p.y;
                float idx =
                    1.0*mod(x,2.0) + 2.0*mod(y,2.0) +
                    4.0*mod(floor(x/2.0),2.0) + 8.0*mod(floor(y/2.0),2.0) +
                    16.0*mod(floor(x/4.0),2.0) + 32.0*mod(floor(y/4.0),2.0);
                return (idx + 0.5) / 64.0;
            }

            void main() {
                vec2 norm = gl_FragCoord.xy / uResolution;
                vec2 uv   = norm * 2.0 - 1.0;
                uv.x     *= uResolution.x / uResolution.y;

                float t   = uTime * 0.45;
                float amp = clamp(uAmplitude, 0.0, 1.6);

                // Ocean sound wave ripples
                float radius    = 0.08 + amp * 0.42 + sin(t * 1.2) * 0.007;
                float thickness = 0.030 + amp * 0.15 + sin(t * 0.8) * 0.005;

                float dist  = length(uv);
                float ring  = smoothstep(radius + thickness, radius, dist)
                            - smoothstep(radius, radius - thickness, dist);
                float glow  = exp(-12.0 * abs(dist - radius) / (1.0 + amp * 0.8));
                float halo  = exp(-4.5 * dist * (1.0 - amp * 0.3));

                float intensity = clamp(ring * 0.90 + glow * 0.65 + halo * 0.18, 0.0, 1.0);
                float threshold = bayerDither(gl_FragCoord.xy);
                float shade     = step(threshold, intensity);

                // Soft Tropical & Ocean Wave Palette
                vec3 oceanMuted = vec3(0.47, 0.66, 0.63); // #78A9A0 Muted Ocean Teal
                vec3 warmCream  = vec3(0.96, 0.92, 0.87); // #F5EBDD Warm Cream
                vec3 softCoral  = vec3(0.85, 0.51, 0.42); // #D9826B Soft Terracotta

                vec3 color = mix(oceanMuted, warmCream, clamp(intensity * 1.2, 0.0, 1.0));
                color = mix(color, softCoral, clamp(amp * 0.35, 0.0, 0.5));

                gl_FragColor = vec4(color * shade, shade * 0.96);
            }
        `;

        function mkShader(type, src) {
            const s = gl.createShader(type);
            gl.shaderSource(s, src);
            gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
                const msg = gl.getShaderInfoLog(s);
                gl.deleteShader(s);
                throw new Error(msg);
            }
            return s;
        }

        function resize() {
            if (!canvas || !gl) return;
            const r   = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const w   = Math.round(r.width  * dpr);
            const h   = Math.round(r.height * dpr);
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width  = w;
                canvas.height = h;
            }
            gl.viewport(0, 0, w, h);
        }

        function render(time) {
            animId = requestAnimationFrame(render);
            if (!gl || !prog) return;

            resize();
            gl.useProgram(prog);
            gl.clearColor(0.078, 0.20, 0.15, 1.0);
            gl.clear(gl.COLOR_BUFFER_BIT);

            if (currentState === "idle") {
                const idleBreath = 0.025 + 0.02 * (0.5 + 0.5 * Math.sin(time * 0.0016));
                targetAmplitude = idleBreath;
            } else if (currentState === "processing") {
                const pulseProcessing = 0.18 + 0.12 * (0.5 + 0.5 * Math.sin(time * 0.005));
                targetAmplitude = pulseProcessing;
            }

            const easeFactor = (targetAmplitude > amplitude) ? 0.26 : 0.085;
            amplitude += (targetAmplitude - amplitude) * easeFactor;

            if (uniforms.time)       gl.uniform1f(uniforms.time, time * 0.001);
            if (uniforms.amplitude)  gl.uniform1f(uniforms.amplitude, amplitude);
            if (uniforms.resolution) gl.uniform2f(uniforms.resolution, gl.drawingBufferWidth, gl.drawingBufferHeight);

            if (sphereWrapper) {
                const scale       = 1.0 + amplitude * 0.10;
                const glowSize    = 25 + amplitude * 120;
                const glowOpacity = 0.15 + amplitude * 0.45;
                sphereWrapper.style.transform = `scale(${scale.toFixed(4)})`;
                sphereWrapper.style.boxShadow = `
                    0 0 0 1.5px rgba(245, 235, 221, ${(0.22 + amplitude * 0.35).toFixed(3)}),
                    0 8px 24px rgba(0, 0, 0, 0.35),
                    0 0 ${glowSize.toFixed(1)}px rgba(120, 169, 160, ${glowOpacity.toFixed(3)})
                `;
            }

            gl.drawArrays(gl.TRIANGLES, 0, 6);
        }

        function init() {
            if (!canvas) return;
            try {
                gl = canvas.getContext("webgl", {
                    antialias: false,
                    premultipliedAlpha: true,
                    preserveDrawingBuffer: false
                });
                if (!gl) { console.warn("WebGL not supported"); return; }

                const vert = mkShader(gl.VERTEX_SHADER,   VERT);
                const frag = mkShader(gl.FRAGMENT_SHADER, FRAG);

                prog = gl.createProgram();
                gl.attachShader(prog, vert);
                gl.attachShader(prog, frag);
                gl.linkProgram(prog);
                if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
                gl.deleteShader(vert);
                gl.deleteShader(frag);

                const verts = new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]);
                const buf   = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, buf);
                gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);

                const posLoc = gl.getAttribLocation(prog, "aPosition");
                gl.enableVertexAttribArray(posLoc);
                gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

                gl.useProgram(prog);
                gl.disable(gl.DEPTH_TEST);
                gl.disable(gl.CULL_FACE);
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

                uniforms = {
                    time:       gl.getUniformLocation(prog, "uTime"),
                    amplitude:  gl.getUniformLocation(prog, "uAmplitude"),
                    resolution: gl.getUniformLocation(prog, "uResolution")
                };

                render(0);
            } catch (err) {
                console.error("VoiceDictator WebGL error:", err);
            }
        }

        function setState(state) {
            currentState = state;
            if (state === "idle") {
                targetAmplitude = 0.03;
            } else if (state === "processing") {
                targetAmplitude = 0.25;
            }
        }

        function setLiveLoudness(loudness) {
            if (currentState === "listening" || currentState === "speaking") {
                targetAmplitude = Math.min(1.5, Math.max(0.03, loudness));
            }
        }

        function destroy() {
            if (animId) cancelAnimationFrame(animId);
        }

        return { init, setState, setLiveLoudness, destroy };
    })();

    VoiceDictator.init();


    // ============================================================
    // 5. TYPEWRITER EFFECT
    // ============================================================
    function typewriter(element, text, speed = 18, onComplete) {
        element.innerHTML = "";
        let index = 0;

        const cursor = document.createElement("span");
        cursor.className = "typewriter-cursor";
        cursor.textContent = "|";
        element.appendChild(cursor);

        function tick() {
            if (index < text.length) {
                cursor.insertAdjacentText("beforebegin", text[index]);
                index++;
                setTimeout(tick, speed);
            } else {
                setTimeout(() => {
                    cursor.style.animation   = "none";
                    cursor.style.opacity     = "0";
                    cursor.style.transition  = "opacity .4s";
                }, 700);
                if (typeof onComplete === "function") onComplete();
            }
        }
        setTimeout(tick, speed);
    }


    // ============================================================
    // 6. NUMBER TICKER
    // ============================================================
    function tickNumber(element, target, duration = 750) {
        const start   = performance.now();
        const decimals = target < 1 ? 3 : target < 10 ? 2 : 1;

        function update(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased    = 1 - Math.pow(1 - progress, 4);
            element.textContent = (target * eased).toFixed(decimals);
            if (progress < 1) requestAnimationFrame(update);
            else element.textContent = target.toFixed(decimals);
        }
        requestAnimationFrame(update);
    }


    // ============================================================
    // 7. DOM ELEMENT REFERENCES & STATE MANAGEMENT
    // ============================================================
    const questionInput     = document.getElementById("question-input");
    const topKSlider        = document.getElementById("top-k-slider");
    const topKVal           = document.getElementById("top-k-val");
    const ragForm           = document.getElementById("rag-form");
    const submitBtn         = document.getElementById("submit-btn");
    const promptChips       = document.querySelectorAll(".chip");

    const micBtn            = document.getElementById("mic-btn");
    const voiceStatusLabel  = document.getElementById("voice-status-label");
    const oracleSubhint     = document.getElementById("oracle-subhint");
    const transcriptionCard = document.getElementById("transcription-card");
    const transcriptionText = document.getElementById("transcription-text");
    const liveSpeechStatus  = document.getElementById("live-speech-status");
    const livePulseDot      = document.getElementById("live-pulse-dot");
    const speechHint        = document.getElementById("speech-hint");
    const clearMemoryBtn    = document.getElementById("clear-memory-btn");

    const placeholderState  = document.getElementById("placeholder-state");
    const resultCard        = document.getElementById("result-card");
    const answerContent     = document.getElementById("answer-content");
    const performanceBar    = document.getElementById("performance-bar");
    const copyAnsBtn        = document.getElementById("copy-ans-btn");
    const copyBtnText       = document.getElementById("copy-btn-text");
    const replayAudioBtn    = document.getElementById("replay-audio-btn");
    const agentAudio        = document.getElementById("agent-audio");

    const sourcesCard       = document.getElementById("sources-card");
    const sourcesCount      = document.getElementById("sources-count");
    const sourcesList       = document.getElementById("sources-list");

    const statusPillText    = document.getElementById("status-text");
    const statusGem         = document.querySelector(".status-gem");
    const metaSTT           = document.getElementById("meta-stt");
    const metaLLM           = document.getElementById("meta-llm");
    const metaTTS           = document.getElementById("meta-tts");

    // Unified Voice State Machine & Session Control
    let currentVoiceState      = "idle"; // "idle" | "listening" | "processing" | "speaking"
    let currentSessionId       = 0;      // Incremented on interruptions to cancel stale callbacks
    let activeAbortController  = null;   // Aborts in-flight network requests
    let audioContext           = null;
    let audioStream            = null;
    let scriptProcessor        = null;
    let audioInput             = null;
    let recordingBuffer        = [];
    let sampleRate             = 0;
    let currentAudioBase64     = null;
    let liveRecognition        = null;
    let silenceTimeout         = null;
    let liveFinalTranscript    = "";
    let liveInterimTranscript  = "";

    // TTS Web Audio Reactivity nodes
    let ttsAudioCtx  = null;
    let ttsAnalyser  = null;
    let ttsSource    = null;
    let ttsAnimId    = null;


    // ============================================================
    // 8. TOP-K SLIDER
    // ============================================================
    topKSlider.addEventListener("input", (e) => {
        topKVal.textContent = e.target.value;
    });


    // ============================================================
    // 9. QUICK PROMPT CHIPS
    // ============================================================
    promptChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            stopAISpeech();
            questionInput.value = chip.dataset.query;
            ragForm.dispatchEvent(new Event("submit"));
        });
    });


    // ============================================================
    // 10. HEALTH CHECK ON STARTUP
    // ============================================================
    async function checkHealth() {
        try {
            const resp = await fetch("/health");
            const data = await resp.json();
            if (data.status === "healthy") {
                statusPillText.textContent = `System Active (${data.total_indexed_documents} indexed)`;
                if (statusGem) statusGem.style.backgroundColor = "var(--ocean-muted)";
            } else {
                statusPillText.textContent = "Degraded — check index";
                if (statusGem) statusGem.style.backgroundColor = "var(--accent-ochre)";
                Toast.warning("System Notice", "Vector index status is degraded.");
            }
            if (data.stt_provider) metaSTT.textContent = data.stt_provider.toUpperCase();
            if (data.llm_provider) metaLLM.textContent = data.llm_provider.toUpperCase();
            if (data.tts_provider) metaTTS.textContent = data.tts_provider.toUpperCase();
        } catch (err) {
            statusPillText.textContent = "Oracle Offline";
            if (statusGem) statusGem.style.backgroundColor = "var(--coral-soft)";
            Toast.error("Connection Notice", "Cannot reach the API server.");
        }
    }
    checkHealth();


    // ============================================================
    // 11. CLEAR MEMORY
    // ============================================================
    clearMemoryBtn.addEventListener("click", async () => {
        try {
            stopAISpeech();
            const resp = await fetch("/api/memory/clear", { method: "POST" });
            const data = await resp.json();
            Toast.success("Memory Purified", data.message || "Conversational history reset.");
        } catch (err) {
            Toast.error("Error", "Failed to clear memory.");
        }
    });


    // ============================================================
    // 12. REPLAY AUDIO + COPY ANSWER
    // ============================================================
    replayAudioBtn.addEventListener("click", () => {
        if (currentAudioBase64) {
            stopAISpeech();
            currentSessionId++;
            playAudio(currentAudioBase64, currentSessionId);
        }
    });

    copyAnsBtn.addEventListener("click", () => {
        const text = answerContent.innerText || answerContent.textContent;
        navigator.clipboard.writeText(text).then(() => {
            copyBtnText.textContent = "✓ Inscribed!";
            copyAnsBtn.style.color  = "var(--sand-warm)";
            setTimeout(() => {
                copyBtnText.textContent = "Copy Inscription";
                copyAnsBtn.style.color  = "";
            }, 2000);
        }).catch(() => {
            Toast.error("Copy Failed", "Could not access clipboard.");
        });
    });


    // ============================================================
    // 13. CENTRAL VOICE STATE UPDATE HELPER
    // ============================================================
    function updateMicState(state, message) {
        currentVoiceState = state;
        if (voiceStatusLabel) voiceStatusLabel.textContent = message;
        VoiceDictator.setState(state);
    }


    // ============================================================
    // 14. COMPLETE & IMMEDIATE SPEECH / AUDIO INTERRUPTION
    // ============================================================
    function stopAISpeech() {
        // 1. Invalidate current session ID immediately so no stale callbacks run
        currentSessionId++;

        // 2. Cancel Browser SpeechSynthesis if active
        if (window.speechSynthesis) {
            try {
                window.speechSynthesis.cancel();
            } catch (e) {
                console.warn("SpeechSynthesis cancel notice:", e);
            }
        }

        // 3. Pause & unload HTML5 Audio element immediately
        if (agentAudio) {
            try {
                agentAudio.pause();
                agentAudio.removeAttribute("src");
                agentAudio.load();
            } catch (e) {
                console.warn("agentAudio stop notice:", e);
            }
        }

        // 4. Cancel active animation & suspend Web Audio Context
        if (ttsAnimId) {
            cancelAnimationFrame(ttsAnimId);
            ttsAnimId = null;
        }
        if (ttsAudioCtx && ttsAudioCtx.state === "running") {
            try { ttsAudioCtx.suspend(); } catch (e) {}
        }

        // 5. Abort in-flight network request
        if (activeAbortController) {
            try { activeAbortController.abort(); } catch (e) {}
            activeAbortController = null;
        }

        // 6. Clear silence timer
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }

        // 7. Reset Visual & Status indicators
        updateMicState("idle", "Tap sphere to speak");
        if (liveSpeechStatus) liveSpeechStatus.textContent = "Standby";
        if (livePulseDot) livePulseDot.classList.remove("active");
        if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
        if (speechHint) speechHint.textContent = "Click the sphere again to complete your question";
        Loader.hide();
    }


    // ============================================================
    // 15. TEXT FORM SUBMISSION (WITH CANCELLATION SUPPORT)
    // ============================================================
    ragForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;

        // Stop any current speech before text query
        stopAISpeech();
        const thisSessionId = currentSessionId;

        const topK = parseInt(topKSlider.value, 10);
        submitBtn.disabled = true;
        submitBtn.querySelector(".btn-text").textContent = "Consulting Scroll…";
        Loader.show("Searching the Knowledge Archive…");
        updateMicState("processing", "Thinking…");
        if (liveSpeechStatus) liveSpeechStatus.textContent = "Thinking...";

        activeAbortController = new AbortController();

        try {
            const response = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question, top_k: topK }),
                signal: activeAbortController.signal
            });

            if (thisSessionId !== currentSessionId) return; // Stale session ignored

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server error");
            }

            const data = await response.json();
            if (thisSessionId !== currentSessionId) return;

            currentAudioBase64 = null;
            replayAudioBtn.classList.add("hidden");
            data.transcript = question;
            data.retrieved_documents = data.retrieved_documents || [];
            
            transcriptionText.textContent = question;
            if (liveSpeechStatus) liveSpeechStatus.textContent = "Inscribed";
            updateMicState("idle", "Tap sphere to speak");
            
            renderResults(data);

        } catch (err) {
            if (thisSessionId === currentSessionId && err.name !== "AbortError") {
                updateMicState("idle", "Tap sphere to speak");
                if (liveSpeechStatus) liveSpeechStatus.textContent = "Error";
                Toast.error("Oracle Notice", err.message);
            }
        } finally {
            Loader.hide();
            submitBtn.disabled = false;
            submitBtn.querySelector(".btn-text").textContent = "Consult the Oracle";
        }
    });


    // ============================================================
    // 16. MICROPHONE BUTTON INTELLIGENT TOGGLE HANDLER
    // ============================================================
    micBtn.addEventListener("click", () => {
        if (currentVoiceState === "speaking") {
            // STATE 3: AI IS SPEAKING -> INTERRUPT IMMEDIATELY & START LISTENING FOR NEXT QUESTION
            stopAISpeech();
            startRecording();
        } else if (currentVoiceState === "listening") {
            // STATE 2: CURRENTLY LISTENING -> STOP & SEND
            stopRecordingAndSend();
        } else if (currentVoiceState === "processing") {
            // Processing -> Interrupt and start fresh
            stopAISpeech();
            startRecording();
        } else {
            // STATE 1: IDLE -> START LISTENING
            startRecording();
        }
    });


    // ============================================================
    // 17. START LISTENING (WITH TRUE BARGE-IN & ROBUST SPEECH STREAMING)
    // ============================================================
    async function startRecording() {
        // Stop any old speech first
        stopAISpeech();
        const thisSessionId = currentSessionId;

        recordingBuffer = [];
        liveFinalTranscript = "";
        liveInterimTranscript = "";

        updateMicState("listening", "Listening… Tap to seal");
        if (oracleSubhint) oracleSubhint.textContent = "Speak clearly into your microphone...";
        if (liveSpeechStatus) liveSpeechStatus.textContent = "Listening...";
        if (livePulseDot) livePulseDot.classList.add("active");
        if (transcriptionText) transcriptionText.textContent = "Listening to your voice...";
        if (speechHint) speechHint.textContent = "Tap sphere to send, or pause when finished";

        // 17.1 Web Speech API Live Recognition
        try {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SpeechRec) {
                liveRecognition = new SpeechRec();
                liveRecognition.continuous = true;
                liveRecognition.interimResults = true;
                liveRecognition.lang = "en-US";
                liveRecognition.maxAlternatives = 1;

                liveRecognition.onresult = (event) => {
                    if (thisSessionId !== currentSessionId) return;

                    let interim = "";
                    let finalStr = "";

                    for (let i = 0; i < event.results.length; ++i) {
                        const res = event.results[i];
                        if (res.isFinal) {
                            finalStr += res[0].transcript + " ";
                        } else {
                            interim += res[0].transcript + " ";
                        }
                    }

                    if (finalStr.trim()) {
                        liveFinalTranscript = finalStr.trim();
                    }
                    liveInterimTranscript = interim.trim();

                    const combined = (liveFinalTranscript + " " + liveInterimTranscript).trim();
                    if (combined) {
                        transcriptionText.textContent = combined;

                        // Natural silence auto-send debounce (2.6s silence after user spoke)
                        if (silenceTimeout) clearTimeout(silenceTimeout);
                        silenceTimeout = setTimeout(() => {
                            if (currentVoiceState === "listening" && thisSessionId === currentSessionId) {
                                stopRecordingAndSend();
                            }
                        }, 2600);
                    }
                };

                liveRecognition.onerror = (e) => {
                    console.log("Web Speech API notice:", e.error);
                };

                liveRecognition.onend = () => {
                    // Safe cleanup if recognition stops naturally
                    if (currentVoiceState === "listening" && thisSessionId === currentSessionId && !recordingBuffer.length) {
                        // Keep alive if still recording
                    }
                };

                liveRecognition.start();
            }
        } catch (e) {
            console.log("Web Speech API initialization fallback:", e);
        }

        // 17.2 MediaStream AudioContext Recording & Live Energy Analysis
        try {
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false
            });

            if (thisSessionId !== currentSessionId) {
                audioStream.getTracks().forEach(t => t.stop());
                return;
            }

            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioCtx();
            sampleRate   = audioContext.sampleRate;

            audioInput      = audioContext.createMediaStreamSource(audioStream);
            scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);

            scriptProcessor.onaudioprocess = (e) => {
                if (currentVoiceState !== "listening" || thisSessionId !== currentSessionId) return;
                const channelData = e.inputBuffer.getChannelData(0);
                recordingBuffer.push(new Float32Array(channelData));

                let sumSquares = 0;
                for (let i = 0; i < channelData.length; i++) {
                    sumSquares += channelData[i] * channelData[i];
                }
                const rms = Math.sqrt(sumSquares / channelData.length);
                const voiceLoudness = Math.min(1.5, Math.max(0.03, (rms - 0.002) * 8.5));
                VoiceDictator.setLiveLoudness(voiceLoudness);
            };

            audioInput.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);

        } catch (err) {
            if (thisSessionId === currentSessionId) {
                updateMicState("idle", "Tap sphere to speak");
                if (liveSpeechStatus) liveSpeechStatus.textContent = "Standby";
                if (livePulseDot) livePulseDot.classList.remove("active");
                Toast.error("Microphone Notice", `Microphone access denied: ${err.message}`);
            }
        }
    }


    // ============================================================
    // 18. STOP LISTENING AND SEND QUERY
    // ============================================================
    async function stopRecordingAndSend() {
        if (currentVoiceState !== "listening") return;
        const thisSessionId = currentSessionId;

        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }

        updateMicState("processing", "Thinking…");
        if (oracleSubhint) oracleSubhint.textContent = "Synthesizing neural retrieval response...";
        if (liveSpeechStatus) liveSpeechStatus.textContent = "Thinking...";
        if (livePulseDot) livePulseDot.classList.remove("active");
        Loader.show("Transcribing and retrieving from MSMARCO-XI...");

        // Stop live recognition
        if (liveRecognition) {
            try { liveRecognition.stop(); } catch(e) {}
            liveRecognition = null;
        }

        // Disconnect audio processors
        if (scriptProcessor)  { scriptProcessor.disconnect(); scriptProcessor.onaudioprocess = null; }
        if (audioInput)       { audioInput.disconnect(); }
        if (audioStream)      { audioStream.getTracks().forEach(t => t.stop()); }
        if (audioContext)     { audioContext.close(); }

        const pcmWavBlob = exportWAV(recordingBuffer, sampleRate);
        const capturedSpeechText = (liveFinalTranscript + " " + liveInterimTranscript).trim();

        // Check if there is captured audio or speech text
        if (pcmWavBlob.size < 1000 && !capturedSpeechText) {
            Loader.hide();
            updateMicState("idle", "Tap sphere to speak");
            if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
            if (liveSpeechStatus) liveSpeechStatus.textContent = "Standby";
            Toast.warning("Short Speech", "No speech detected. Please tap and speak clearly.");
            return;
        }

        const topK = parseInt(topKSlider.value, 10);
        const formData = new FormData();
        formData.append("file", pcmWavBlob, "query.wav");

        activeAbortController = new AbortController();

        try {
            const response = await fetch(`/api/ask-voice?top_k=${topK}`, {
                method: "POST",
                body: formData,
                signal: activeAbortController.signal
            });

            if (thisSessionId !== currentSessionId) return; // Discard stale session

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Voice RAG processing failed.");
            }

            const data = await response.json();
            if (thisSessionId !== currentSessionId) return;

            renderResults(data);

            if (transcriptionText && data.transcript) {
                transcriptionText.textContent = data.transcript;
            }
            if (liveSpeechStatus) liveSpeechStatus.textContent = "Inscribed";

            if (data.audio) {
                currentAudioBase64 = data.audio;
                replayAudioBtn.classList.remove("hidden");
                playAudio(data.audio, thisSessionId);
            } else {
                updateMicState("idle", "Tap sphere to speak");
                if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
            }

        } catch (err) {
            if (thisSessionId === currentSessionId && err.name !== "AbortError") {
                updateMicState("idle", "Tap sphere to speak");
                if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
                if (liveSpeechStatus) liveSpeechStatus.textContent = "Error";
                Toast.error("Oracle Notice", err.message);
            }
        } finally {
            Loader.hide();
        }
    }


    // ============================================================
    // 19. TTS AUDIO PLAYBACK WITH IMMEDIATE INTERRUPTIBILITY
    // ============================================================
    function playAudio(audioBase64, sessionId) {
        if (sessionId !== currentSessionId) return; // Discard stale audio

        updateMicState("speaking", "Speaking… Tap to interrupt");
        if (oracleSubhint) oracleSubhint.textContent = "Oracle voice synthesis in progress... Tap sphere to stop.";
        if (liveSpeechStatus) liveSpeechStatus.textContent = "Speaking...";
        if (speechHint) speechHint.textContent = "Tap the sphere at any time to interrupt and ask another question";

        agentAudio.src = audioBase64;
        const playPromise = agentAudio.play();
        if (playPromise !== undefined) {
            playPromise.catch(e => {
                console.log("Audio play notice:", e);
            });
        }

        try {
            if (!ttsAudioCtx) {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                ttsAudioCtx = new AudioCtx();
                ttsAnalyser = ttsAudioCtx.createAnalyser();
                ttsAnalyser.fftSize = 256;
                ttsSource = ttsAudioCtx.createMediaElementSource(agentAudio);
                ttsSource.connect(ttsAnalyser);
                ttsAnalyser.connect(ttsAudioCtx.destination);
            }

            if (ttsAudioCtx.state === "suspended") {
                ttsAudioCtx.resume();
            }

            const pcmData = new Uint8Array(ttsAnalyser.frequencyBinCount);
            function trackTTSVolume() {
                if (sessionId !== currentSessionId || agentAudio.paused || agentAudio.ended) {
                    cancelAnimationFrame(ttsAnimId);
                    return;
                }
                ttsAnalyser.getByteFrequencyData(pcmData);
                let sum = 0;
                for (let i = 0; i < pcmData.length; i++) sum += pcmData[i];
                const avg = sum / pcmData.length;
                const ttsLoudness = Math.min(1.4, Math.max(0.04, (avg / 128.0) * 1.5));
                VoiceDictator.setLiveLoudness(ttsLoudness);
                ttsAnimId = requestAnimationFrame(trackTTSVolume);
            }
            trackTTSVolume();

        } catch (e) {
            const fallbackIv = setInterval(() => {
                if (sessionId !== currentSessionId || agentAudio.paused || agentAudio.ended) {
                    clearInterval(fallbackIv);
                    return;
                }
                VoiceDictator.setLiveLoudness(0.2 + Math.random() * 0.6);
            }, 100);
        }

        agentAudio.onended = () => {
            if (sessionId === currentSessionId) {
                if (ttsAnimId) cancelAnimationFrame(ttsAnimId);
                updateMicState("idle", "Tap sphere to speak");
                if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
                if (liveSpeechStatus) liveSpeechStatus.textContent = "Standby";
                if (speechHint) speechHint.textContent = "Click the sphere again to ask another question";
            }
        };

        agentAudio.onerror = () => {
            if (sessionId === currentSessionId) {
                if (ttsAnimId) cancelAnimationFrame(ttsAnimId);
                updateMicState("idle", "Tap sphere to speak");
                if (oracleSubhint) oracleSubhint.textContent = "Chant your query aloud to awaken the knowledge archive";
                if (liveSpeechStatus) liveSpeechStatus.textContent = "Standby";
            }
        };
    }


    // ============================================================
    // 20. RENDER RESULTS
    // ============================================================
    function renderResults(data) {
        placeholderState.classList.add("hidden");
        resultCard.classList.remove("hidden");
        sourcesCard.classList.remove("hidden");

        answerContent.innerHTML = "";
        typewriter(answerContent, data.answer || "No revelation inscribed.", 18);

        const meta = data.metadata || {};
        performanceBar.innerHTML = "";

        const metricDefs = [
            { key: "stt_time_sec",        label: "STT",        unit: "s" },
            { key: "retrieval_time_sec",   label: "Retrieval",  unit: "s" },
            { key: "generation_time_sec",  label: "Synthesis",  unit: "s" },
            { key: "tts_time_sec",         label: "Voice",      unit: "s" },
            { key: "total_time_sec",       label: "Total",      unit: "s" }
        ];

        metricDefs.forEach(({ key, label, unit }) => {
            if (meta[key] === undefined) return;
            const item    = document.createElement("div");
            item.className = "perf-item";

            const labelEl = document.createElement("span");
            labelEl.className   = "perf-label";
            labelEl.textContent = label;

            const valEl = document.createElement("span");
            valEl.className   = "perf-val";
            valEl.textContent = "0.000";

            item.appendChild(labelEl);
            item.appendChild(valEl);
            performanceBar.appendChild(item);

            tickNumber(valEl, parseFloat(meta[key]) || 0, 750);
        });

        if (meta.cached) {
            const item    = document.createElement("div");
            item.className = "perf-item";
            item.innerHTML = `
                <span class="perf-label">Cache</span>
                <span class="perf-val" style="color:var(--ocean-muted)">⚡ HIT</span>
            `;
            performanceBar.appendChild(item);
        }

        sourcesCount.textContent = data.sources ? data.sources.length : 0;
        sourcesList.innerHTML    = "";

        if (data.sources && data.sources.length > 0) {
            data.sources.forEach((source, idx) => {
                const item = document.createElement("div");
                item.className = "source-item";
                item.innerHTML = `
                    <div class="source-header">
                        <span class="source-title">${idx + 1}. ${escapeHtml(source.title || 'Document')} (ID: ${source.id})</span>
                        <span class="source-score">Similarity: ${source.score}</span>
                    </div>
                    <div class="source-text">${escapeHtml(source.text)}</div>
                `;
                sourcesList.appendChild(item);
            });
        } else {
            sourcesList.innerHTML = `<p style="color:var(--text-muted);font-size:.875rem;">No evidence passages retrieved.</p>`;
        }
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }


    // ============================================================
    // 21. WAV EXPORT HELPERS
    // ============================================================
    function exportWAV(buffers, originalSampleRate) {
        const targetSampleRate   = 16000;
        const merged             = mergeBuffers(buffers);
        const downsampled        = downsampleBuffer(merged, originalSampleRate, targetSampleRate);
        const buffer             = new ArrayBuffer(44 + downsampled.length * 2);
        const view               = new DataView(buffer);

        writeString(view, 0,  "RIFF");
        view.setUint32(4,  36 + downsampled.length * 2, true);
        writeString(view, 8,  "WAVE");
        writeString(view, 12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20,  1, true);
        view.setUint16(22,  1, true);
        view.setUint32(24, targetSampleRate, true);
        view.setUint32(28, targetSampleRate * 2, true);
        view.setUint16(32,  2, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, "data");
        view.setUint32(40, downsampled.length * 2, true);

        let offset = 44;
        for (let i = 0; i < downsampled.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, downsampled[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return new Blob([view], { type: "audio/wav" });
    }

    function mergeBuffers(buffers) {
        let total = 0;
        buffers.forEach(b => total += b.length);
        const result = new Float32Array(total);
        let offset = 0;
        buffers.forEach(b => { result.set(b, offset); offset += b.length; });
        return result;
    }

    function downsampleBuffer(buffer, fromRate, toRate) {
        if (fromRate === toRate) return buffer;
        const ratio     = fromRate / toRate;
        const newLen    = Math.round(buffer.length / ratio);
        const result    = new Float32Array(newLen);
        let   outOffset = 0, inOffset = 0;
        while (outOffset < result.length) {
            const nextIn = Math.round((outOffset + 1) * ratio);
            let accum = 0, count = 0;
            for (let i = inOffset; i < nextIn && i < buffer.length; i++) {
                accum += buffer[i]; count++;
            }
            result[outOffset] = count > 0 ? accum / count : 0;
            outOffset++;
            inOffset = nextIn;
        }
        return result;
    }

    function writeString(view, offset, str) {
        for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    }

});
