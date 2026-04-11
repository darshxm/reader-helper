// Compute MD5 hash of file bytes in the browser (same key as desktop app)
import SparkMD5 from "spark-md5";

export async function hashFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunkSize = 2 * 1024 * 1024; // 2MB chunks
    const chunks = Math.ceil(file.size / chunkSize);
    const spark = new SparkMD5.ArrayBuffer();
    const reader = new FileReader();
    let current = 0;

    function loadChunk() {
      const start = current * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      reader.readAsArrayBuffer(file.slice(start, end));
    }

    reader.onload = (e) => {
      spark.append(e.target!.result as ArrayBuffer);
      current++;
      if (current < chunks) {
        loadChunk();
      } else {
        resolve(spark.end());
      }
    };

    reader.onerror = reject;
    loadChunk();
  });
}
