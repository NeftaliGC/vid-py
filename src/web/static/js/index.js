const params = new URLSearchParams(window.location.search);

if (params.has('id_video')) {
        console.log("ID de video encontrado en los parámetros de la URL.");
        let videoId = params.get('id_video');
        let videoLink = `https://www.youtube.com/watch?v=${videoId}`;
        document.getElementById('youtubeLink').value = videoLink;
        mostrarMiniatura(false);
}

function cerrarBanner() {
    document.getElementById('warningBanner').style.display = 'none';
}

function mostrarMiniatura(forzarRedireccion = true) {
    const link = document.getElementById('youtubeLink').value;
    const previewContainer = document.getElementById('thumbnailPreview');
    const thumbnailImg = document.getElementById('videoThumbnail');
    const videobtn = document.getElementById('videoBtn');
    const audiobtn = document.getElementById('audioBtn');
    const videoId = extraerVideoID(link);

    if (videoId) {
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('id_video', videoId);
        window.history.replaceState({}, '', newUrl);
        if (forzarRedireccion) {
            window.location.href = newUrl.toString();
            return;
        }

        if (audiobtn != null && videobtn != null) {
            videobtn.href = `/descargar-video/?id_video=${videoId}`;
            audiobtn.href = `/descargar-audio/?id_video=${videoId}`;
        }
        document.getElementById("video").scrollIntoView({ behavior: "smooth" });
        thumbnailImg.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
        previewContainer.style.display = 'block';
    } else {
        document.getElementById("top").scrollIntoView({ behavior: "smooth" });
        previewContainer.style.display = 'none';
        thumbnailImg.src = '';
    }
}

function extraerVideoID(url) {
    const regex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}
