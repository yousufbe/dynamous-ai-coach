
// A mapping from file extensions to IANA MIME types.
const mimeTypeMap: { [key: string]: string } = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
};

/**
 * Converts a File object to a GoogleGenerativeAI.Part object.
 */
export async function fileToGenerativePart(file: File) {
    const base64EncodedDataPromise = new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            if (typeof reader.result === 'string') {
                // remove the "data:mime/type;base64," prefix
                resolve(reader.result.split(',')[1]);
            } else {
                resolve(''); // Should not happen with readAsDataURL
            }
        };
        reader.readAsDataURL(file);
    });

    return {
        inlineData: {
            data: await base64EncodedDataPromise,
            mimeType: file.type || getMimeType(file.name),
        },
    };
}


function getMimeType(fileName: string): string {
    const extension = fileName.split('.').pop()?.toLowerCase();
    return extension && mimeTypeMap[extension] ? mimeTypeMap[extension] : 'application/octet-stream';
}
