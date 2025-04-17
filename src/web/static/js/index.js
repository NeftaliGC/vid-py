function cerrarBanner() {
    document.getElementById('warningBanner').style.display = 'none';
}

function mostrarMiniatura() {
    const link = document.getElementById('youtubeLink').value;
    const previewContainer = document.getElementById('thumbnailPreview');
    const thumbnailImg = document.getElementById('videoThumbnail');
    
    const videoId = extraerVideoID(link);

    if (videoId) {
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