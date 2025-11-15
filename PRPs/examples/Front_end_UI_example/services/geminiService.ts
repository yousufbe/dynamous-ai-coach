
import { GoogleGenAI } from "@google/genai";
import { fileToGenerativePart } from '../utils/fileUtils';

const API_KEY = process.env.API_KEY;

if (!API_KEY) {
    throw new Error("API_KEY environment variable not set.");
}

const ai = new GoogleGenAI({ apiKey: API_KEY });

export const generateContentWithFiles = async (prompt: string, files: File[]): Promise<string> => {
    const model = ai.models['gemini-2.5-flash'];
    
    if (files.length === 0) {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
        });
        return response.text;
    }

    const fileParts = await Promise.all(
        files.map(file => fileToGenerativePart(file))
    );

    const parts = [
        ...fileParts,
        { text: prompt },
    ];
    
    const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: { parts: parts },
    });
    
    return response.text;
};
