const btn = document.getElementById('btn');
const out = document.getElementById('out');

btn.onclick = async () => {
  btn.disabled = true;
  out.innerText = "🔄 Analizando tu PC...";

  // Recoger valores del formulario
  const data = {
    cpu_model: document.getElementById('cpu_model').value,
    cpu_speed_ghz: parseFloat(document.getElementById('cpu_speed_ghz').value) || 1.0,
    cores: parseInt(document.getElementById('cores').value) || 1,
    ram_gb: parseFloat(document.getElementById('ram_gb').value) || 1.0,
    disk_type: document.getElementById('disk_type').value || "HDD",
    gpu_model: document.getElementById('gpu_model').value || "",
    gpu_vram_gb: parseFloat(document.getElementById('gpu_vram_gb').value) || 0
  };

  try {
    // Llamar al backend FastAPI en OpenShift
    const res = await fetch("https://analiza-tu-pc-analizatupc-dev.apps.rm1.0a51.p1.openshiftapps.com/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data)
    });

    const result = await res.json();

    let text = `✅ Análisis completado!\n\n🎯 Perfil principal: ${result.result.main_profile} (${result.result.main_score}%)\n\n`;
    text += "📈 Adecuación por perfiles:\n";
    for (const [profile, score] of Object.entries(result.result.scores)) {
      text += `• ${profile}: ${(score * 100).toFixed(1)}%\n`;
    }

    text += "\n📎 Descargas:\n";
    if (result.pdf_url) text += `PDF: ${result.pdf_url}\n`;
    if (result.json_url) text += `JSON: ${result.json_url}\n`;
    if (!result.pdf_url && !result.json_url) text += "⚠️ No se subieron archivos a Dropbox.\n";

    out.innerText = text;
  } catch (e) {
    out.innerText = "❌ Error conectando con el backend:\n" + e.toString();
    console.error(e);
  } finally {
    btn.disabled = false;
  }
};