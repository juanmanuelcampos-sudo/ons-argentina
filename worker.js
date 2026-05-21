// Cloudflare Worker — proxy para BYMA open data
// Resuelve el problema de CORS: el worker consulta BYMA server-side
// y devuelve la respuesta con los headers correctos para que el browser la acepte.

const BYMA_URL =
  "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/bnown/obligaciones-negociables";

export default {
  async fetch(request) {
    // Permitir preflight CORS
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    try {
      const bymaRes = await fetch(BYMA_URL, {
        headers: {
          "Accept": "application/json",
          "Referer": "https://open.bymadata.com.ar/",
          "Origin": "https://open.bymadata.com.ar",
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
      });

      const body = await bymaRes.text();

      return new Response(body, {
        status: bymaRes.status,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders(),
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders() },
      });
    }
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}
