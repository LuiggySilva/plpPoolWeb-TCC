// Configuração global para lidar com o fechamento de modais via HTMX

document.body.addEventListener('htmx:beforeSwap', function(evt) {
    const triggerHeader = evt.detail.xhr.getResponseHeader('HX-Trigger');
    if (!triggerHeader) return;

    try {
        const config = JSON.parse(triggerHeader);
        
        if (config.closeModal) {
            const data = config.closeModal;

            if (data.target) {
                evt.detail.target = document.querySelector(data.target);
            }
            
            evt.detail.shouldSwap = true;
            if (data.modal) {
                const modalEl = document.querySelector(data.modal);
                const inst = bootstrap.Modal.getInstance(modalEl);
                if (inst) inst.hide();
            }

            if (data.listModal) {
                const listModalEl = document.querySelector(data.listModal);
                const listModal = bootstrap.Modal.getOrCreateInstance(listModalEl);
                
                setTimeout(() => {
                    listModal.show();
                }, 150); 
            }
        }
    } catch (e) {
        if (triggerHeader === 'closeModal') {
            console.warn("Trigger 'closeModal' recebido sem instruções JSON.");
        }
    }
});