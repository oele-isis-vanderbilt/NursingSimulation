async function captureScreen() {
    const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
            cursor: 'always',
            width: 1280,
            height: 720,
            frameRate: 30,
        },
        audio: {
            echoCancellation: true,
            sampleRate: 16000
        }
    });

    return stream;
}

async function checkState(pc) {
    return new Promise((resolve, reject) => {
        if (pc.iceGatheringState === 'complete') {
            resolve();
        } else {
            function _checkState() {
                if (pc.iceGatheringState === 'complete') {
                    pc.removeEventListener('icegatheringstatechange', _checkState);
                    resolve();
                } else if (pc.iceGatheringState === 'failed') {
                    pc.removeEventListener('icegatheringstatechange', _checkState);
                    reject();
                }
            }

            pc.addEventListener('icegatheringstatechange', _checkState);
        }
    })
}

async function startSharing(v) {
    const stream = await captureScreen();
    const config = {
        sdpSemantics: 'unified-plan',
    };

    const pc = new RTCPeerConnection(config);

    pc.addEventListener('track', async (event) => {
        v.srcObject = event.streams[0];
    });

    stream.getTracks().forEach(track => pc.addTrack(track, stream));

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await checkState(pc);
    const response = await fetch('/offer', {
        body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type,
        }),
        headers: {
            'Content-Type': 'application/json'
        },
        method: 'POST'
    });
    if (response.status === 200) {
        const answer = await response.json();
        await pc.setRemoteDescription(answer);
    }

    return pc;
}

window.addEventListener('load', () => {
    let pc;
    document.getElementById('start-sharing').addEventListener('click', async () => {
        const v = document.getElementById('screenVideo');
        pc = await startSharing(v);
    });

    document.getElementById('stop-sharing').addEventListener('click', async () => {
        if (pc) {
            if (pc.getTransceivers) {
                pc.getTransceivers().forEach(transceiver => {
                    transceiver.stop();
                });
            }
            pc.getSenders().forEach(sender => {
                sender.track.stop();
            });

            setTimeout(() => {
                pc.close();
            }, 500);
        }
    });

});
