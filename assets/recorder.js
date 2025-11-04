// recorder.js — WAV version (v9 - Send Timer Data)
console.log("recorder.js (v9 - Send Timer Data) has LOADED.");

/*
* This script uses event delegation. A single click listener is attached
* to document.body. This listener persists even when Dash re-renders
* the page content, solving the "unclickable button" bug on navigation.
*/

// --- State variables are defined in a persistent scope ---
let rec_audioContext, rec_mediaStream, rec_processor, rec_input, timerInterval;
let rec_audioData = [];

// --- Attach ONE listener to the document body ---
document.body.addEventListener("click", async (e) => {
    
    // Check if the clicked element (e.target) is our button
    if (e.target && e.target.id === "stt-button") {
        
        console.log("STT Button Clicked (via delegation)");
        const button = e.target; // This is the button element

        if (button.innerText === "🎤 Record Argument") {
            try {
                console.log("Requesting microphone access...");
                rec_mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                rec_audioContext = new (window.AudioContext || window.webkitAudioContext)();
                rec_input = rec_audioContext.createMediaStreamSource(rec_mediaStream);
                
                // Using ScriptProcessorNode (deprecated but widely supported)
                rec_processor = rec_audioContext.createScriptProcessor(4096, 1, 1);

                rec_input.connect(rec_processor);
                rec_processor.connect(rec_audioContext.destination);

                rec_audioData = []; // Clear previous data

                rec_processor.onaudioprocess = (e_audio) => {
                    rec_audioData.push(new Float32Array(e_audio.inputBuffer.getChannelData(0)));
                };

                button.innerText = "⏹️ Stop Recording";
                button.classList.remove("btn-secondary");
                button.classList.add("btn-danger");
                console.log("🎙️ Recording started...");

                // --- NEW: START THE TIMER ---
                const timerElement = document.getElementById('recording-timer');
                if (timerElement) {
                    timerElement.innerText = "00:00"; // Reset timer display
                    let seconds = 0;
                    
                    // Clear any old timer just in case
                    if (timerInterval) {
                        clearInterval(timerInterval);
                    }
                    
                    timerInterval = setInterval(() => {
                        seconds++;
                        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
                        const secs = (seconds % 60).toString().padStart(2, '0');
                        timerElement.innerText = `${mins}:${secs}`;
                    }, 1000);
                }
                // --- END OF NEW TIMER LOGIC ---

            } catch (err) {
                console.error("Microphone error:", err);
                alert("Could not access microphone.");
            }

        } else if (button.innerText === "⏹️ Stop Recording") {
            // Stop recording
            console.log("Stopping recording...");
            rec_processor.disconnect();
            rec_input.disconnect();
            rec_mediaStream.getTracks().forEach((track) => track.stop());

            // Use the sampleRate from the context we created
            const blob = encodeWAV(rec_audioData, 1, rec_audioContext.sampleRate);
            sendToDash(blob); // This helper function is defined below

            button.innerText = "🎤 Record Argument";
            button.classList.remove("btn-danger");
            button.classList.add("btn-secondary");
            console.log("Recording stopped and sent to backend.");

            // --- NEW: STOP THE TIMER ---
            if (timerInterval) {
                clearInterval(timerInterval);
            }
            // --- END OF NEW TIMER LOGIC ---

            // --- NEW: SEND TIMER VALUE TO DASH ---
            const timerElement = document.getElementById('recording-timer');
            if (timerElement) {
                const finalTime = timerElement.innerText;
                const timerStoreId = 'timer-store';
                
                console.log(`📤 Attempting to send timer data: ${finalTime}`);
                
                // Use the same reliable send-to-Dash method
                if (window.dash_clientside && window.dash_clientside.set_props) {
                    window.dash_clientside.set_props(timerStoreId, { data: finalTime });
                    console.log("✅ Timer data sent via dash_clientside.set_props");
                } else if (window.Dash && window.Dash.setProps) {
                    window.Dash.setProps(timerStoreId, { data: finalTime });
                    console.log("✅ Timer data sent via Dash.setProps (legacy)");
                } else {
                    console.error('Could not find Dash.setProps to send timer data.');
                }
            }
            // --- END NEW TIMER SEND LOGIC ---
        }
    }
});


// --- All helper functions remain at the top level of the script ---

/**
 * Converts a Blob to base64 and sends it to the Dash 'stt-output-store'.
 * @param {Blob} blob - The audio blob (e.g., WAV) to send.
 */
function sendToDash(blob) {
    const reader = new FileReader();
    reader.readAsDataURL(blob);
    reader.onloadend = () => {
        const base64Data = reader.result.split(",")[1];
        const storeId = "stt-output-store";
        
        console.log("📤 Attempting to send WAV audio to Dash store...");
        
        // Wait a brief moment to ensure Dash is fully initialized
        setTimeout(() => {
            try {
                // Method 1: Modern Dash clientside API
                if (window.dash_clientside && window.dash_clientside.set_props) {
                    window.dash_clientside.set_props(storeId, { data: base64Data });
                    console.log("✅ Data sent via dash_clientside.set_props");
                    return;
                }
                
                // Method 2: Legacy Dash API
                if (window.Dash && window.Dash.setProps) {
                    window.Dash.setProps(storeId, { data: base64Data });
                    console.log("✅ Data sent via Dash.setProps");
                    return;
                }
                
                // If all methods fail
                console.error("❌ Could not send data to stt-output-store!");
                alert("Failed to send audio. Please try again or check console.");
                
            } catch (error) {
                console.error("❌ Error in sendToDash:", error);
                alert("Error sending audio: " + error.message);
            }
        }, 100); // Small delay to ensure Dash is ready
    };
}

/**
 * Encodes raw Float32 audio samples into a 16-bit PCM WAV file.
 * @param {Float32Array[]} samples - Array of audio chunks.
 * @param {number} numChannels - Number of audio channels.
 * @param {number} sampleRate - The sample rate of the audio.
 * @returns {Blob} A blob object representing the WAV file.
 */
function encodeWAV(samples, numChannels, sampleRate) {
    const merged = mergeBuffers(samples);
    const buffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(buffer);
    
    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + merged.length * 2, true);
    writeString(view, 8, "WAVE");
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, "data");
    view.setUint32(40, merged.length * 2, true);
    floatTo16BitPCM(view, 44, merged);
    
    return new Blob([view], { type: "audio/wav" });
}

function mergeBuffers(chunks) {
    const length = chunks.reduce((acc, c) => acc + c.length, 0);
    const result = new Float32Array(length);
    let offset = 0;
    chunks.forEach((c) => {
        result.set(c, offset);
        offset += c.length;
    });
    return result;
}

function floatTo16BitPCM(output, offset, input) {
    for (let i = 0; i < input.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, input[i]));
        output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}