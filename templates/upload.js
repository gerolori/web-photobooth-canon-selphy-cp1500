// frontend/upload.js

document.addEventListener("alpine:init", () => {
  Alpine.data("uploader", () => ({
    file: null,
    uploading: false,
    progress: 0,
    uploadType: "collage", // default - can be "postcard" or "collage"

    init() {
      // deduce the type from the current page (useful for reuse on postcards.html)
      const path = window.location.pathname.toLowerCase();
      if (path.includes("postcard")) this.uploadType = "postcard";
      else if (path.includes("collage")) this.uploadType = "collage";
    },

    async handleFileChange(event) {
      this.file = event.target.files[0];
      if (!this.file) return;

      await this.uploadFile();
    },

    async uploadFile() {
      if (!this.file) {
        alert("⚠️ Select a file first.");
        return;
      }

      this.uploading = true;
      this.progress = 0;

      const formData = new FormData();
      formData.append("file", this.file);

      // select the right endpoint based on type
      const endpoint =
        this.uploadType === "postcard"
          ? "/api/upload/postcard"
          : "/api/upload/collage";

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const text = await res.text();
          console.error("Upload error:", text);
          alert("❌ Upload error: " + res.status);
          return;
        }

        const data = await res.json();
        console.log("✅ Upload success:", data);

        alert("✅ Photo uploaded successfully!");
      } catch (err) {
        console.error("Upload failed:", err);
        alert("❌ Network error or server unreachable.");
      } finally {
        this.uploading = false;
        this.progress = 100;
      }
    },
  }));
});