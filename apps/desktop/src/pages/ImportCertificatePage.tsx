import { useState } from "react";
import {
  Calendar,
  Check,
  ChevronDown,
  Download,
  FlaskConical,
  Hand,
  Maximize2,
  MessageSquare,
  MoreVertical,
  RotateCw,
  SlidersHorizontal,
  Square,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import {
  CertificateDropzone,
  ImportQueue,
  useCertificateImport,
} from "@/features/certificate-import";

export function ImportCertificatePage() {
  const { items, addFiles, clearFinished } = useCertificateImport();
  const [activeTab, setActiveTab] = useState<"extracted" | "validation" | "analysis" | "history">("extracted");
  const [zoom, setZoom] = useState(100);

  return (
    <div className="flex-1 flex overflow-hidden min-h-0 w-full">
      {/* ========================================================================= */}
      {/* LEFT PANEL: PDF Viewer & Document Canvas                                  */}
      {/* ========================================================================= */}
      <section className="w-[48%] bg-[#2b3341] flex flex-col border-r border-slate-300 shrink-0 select-none min-h-0">
        {/* PDF Document Header Tab */}
        <div className="h-9 bg-[#1f2633] px-3 flex items-center justify-between border-b border-slate-700/60 shrink-0">
          <div className="flex items-center space-x-2 min-w-0">
            <span className="bg-red-500 text-white rounded text-[10px] font-bold px-1.5 py-0.5 leading-tight shrink-0">
              PDF
            </span>
            <span className="text-xs font-medium text-slate-200 truncate">
              Mill_Certificate_784523.pdf
            </span>
          </div>
        </div>

        {/* PDF Toolbar */}
        <div className="h-9 bg-[#262e3d] px-3 flex items-center justify-between text-slate-300 text-xs border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-2">
            <button
              type="button"
              className="hover:text-white p-1 rounded hover:bg-slate-700/50"
              title="Miniaturas"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
            </button>
            <div className="flex items-center space-x-1.5 text-[11px] font-medium text-slate-300 pl-1">
              <span>1</span>
              <span className="text-slate-500">/</span>
              <span>1</span>
            </div>
          </div>

          {/* Zoom & Display Controls */}
          <div className="flex items-center space-x-1.5 text-[11px]">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(50, z - 10))}
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Reducir zoom"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-medium px-1 text-[11px]">{zoom}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(200, z + 10))}
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Aumentar zoom"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <span className="h-3 w-px bg-slate-600 mx-1" />
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Herramienta mano"
            >
              <Hand className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Selección"
            >
              <Square className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Rotar"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Pantalla completa"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Download & Menu */}
          <div className="flex items-center space-x-1">
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Descargar"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              className="hover:text-white p-1 hover:bg-slate-700/50 rounded"
              title="Opciones"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* PDF Document Canvas Scroll Area */}
        <div className="flex-1 overflow-auto p-4 flex flex-col items-center bg-[#434b57] gap-4 min-h-0">
          {/* Integrated Accessible Dropzone */}
          <div className="w-full max-w-[560px]">
            <CertificateDropzone onFilesSelected={addFiles} />
          </div>

          {/* Simulated Physical Paper Document */}
          <div
            className="bg-white w-full max-w-[560px] min-h-[780px] p-8 text-black paper-shadow relative select-text font-sans leading-tight text-[11px] rounded-[2px]"
            style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top center" }}
          >
            {/* Document Header */}
            <div className="flex justify-between items-start border-b border-black pb-4 mb-4">
              <div className="flex items-start space-x-3">
                {/* Company Logo mark */}
                <div className="w-12 h-12 flex items-center justify-center">
                  <svg
                    className="w-12 h-12 stroke-black fill-none stroke-[7]"
                    viewBox="0 0 100 100"
                    aria-hidden="true"
                  >
                    <polygon points="50,10 90,90 10,90" />
                    <line x1="50" x2="75" y1="35" y2="90" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-sm font-black tracking-wide leading-none">
                    ACEROS DEL NORTE S.A. DE C.V.
                  </h1>
                  <p className="text-[9.5px] text-slate-700 mt-1">Parque Industrial #1234</p>
                  <p className="text-[9.5px] text-slate-700">Monterrey, Nuevo León, México</p>
                  <p className="text-[9.5px] text-slate-700">C.P. 66000</p>
                </div>
              </div>
              <div className="text-right">
                <h2 className="text-base font-extrabold tracking-wider">MILL CERTIFICATE</h2>
                <h3 className="text-[10px] font-bold text-slate-800 tracking-wide uppercase">
                  CERTIFICADO DE CALIDAD
                </h3>
                <p className="text-[11px] font-bold mt-2">
                  No. <span className="font-bold">784523</span>
                </p>
                <p className="text-[9.5px] text-slate-600 mt-0.5">
                  Date / Fecha: <span className="font-semibold text-black">2024-02-15</span>
                </p>
              </div>
            </div>

            {/* Customer & Order Information Grid */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] pb-4">
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Customer / Cliente:</span>
                <span className="font-medium uppercase">INDUSTRIAL SUPPLY S.A. DE C.V.</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Material Grade / Grado:</span>
                <span className="font-medium">A36</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Purchase Order / Orden:</span>
                <span className="font-medium">PO-45078</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Dimensions / Dimensiones:</span>
                <span className="font-medium">3.00 mm x 1,500 mm</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Product / Producto:</span>
                <span className="font-medium uppercase">HOT ROLLED STEEL COIL</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Weight / Peso:</span>
                <span className="font-medium">24,580 kg</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Specification / Espec:</span>
                <span className="font-medium">ASTM A36</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Manufacture Date:</span>
                <span className="font-medium">2024-02-10</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Heat No. / Colada No.:</span>
                <span className="font-medium">H34876</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Country of Origin:</span>
                <span className="font-medium">México</span>
              </div>
              <div className="flex">
                <span className="w-32 font-bold shrink-0">Lot No. / Lote No.:</span>
                <span className="font-medium">L-230915</span>
              </div>
            </div>

            {/* Table: Chemical Composition */}
            <div className="mt-2 mb-4">
              <div className="text-[9px] font-bold uppercase tracking-wider mb-1 bg-slate-100 px-1.5 py-0.5 border border-black">
                CHEMICAL COMPOSITION (%)
              </div>
              <table className="w-full text-center border-collapse border border-black text-[9.5px]">
                <thead>
                  <tr className="bg-slate-100 font-bold divide-x divide-black border-b border-black">
                    <th className="py-1">C</th>
                    <th>Mn</th>
                    <th>Si</th>
                    <th>P</th>
                    <th>S</th>
                    <th>Cu</th>
                    <th>Cr</th>
                    <th>Ni</th>
                    <th>Mo</th>
                    <th>V</th>
                    <th>Al</th>
                  </tr>
                </thead>
                <tbody className="divide-x divide-black font-medium">
                  <tr>
                    <td className="py-1">0.17</td>
                    <td>0.85</td>
                    <td>0.24</td>
                    <td>0.012</td>
                    <td>0.008</td>
                    <td>0.20</td>
                    <td>0.03</td>
                    <td>0.02</td>
                    <td>0.01</td>
                    <td>0.002</td>
                    <td>0.035</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Table: Mechanical Properties */}
            <div className="mb-4">
              <div className="text-[9px] font-bold uppercase tracking-wider mb-1 bg-slate-100 px-1.5 py-0.5 border border-black">
                MECHANICAL PROPERTIES
              </div>
              <table className="w-full text-center border-collapse border border-black text-[9.5px]">
                <thead>
                  <tr className="bg-slate-100 font-bold divide-x divide-black border-b border-black">
                    <th className="py-1 px-2">
                      Yield Strength
                      <br />
                      <span className="text-[8px] font-normal">(MPa)</span>
                    </th>
                    <th className="py-1 px-2">
                      Tensile Strength
                      <br />
                      <span className="text-[8px] font-normal">(MPa)</span>
                    </th>
                    <th className="py-1 px-2">
                      Elongation
                      <br />
                      <span className="text-[8px] font-normal">(%)</span>
                    </th>
                    <th className="py-1 px-2">
                      Hardness
                      <br />
                      <span className="text-[8px] font-normal">(HB)</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-x divide-black font-medium">
                  <tr>
                    <td className="py-1.5 font-semibold">250</td>
                    <td className="font-semibold">400</td>
                    <td className="font-semibold">26</td>
                    <td className="font-semibold">120</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Remarks */}
            <div className="mb-5 text-[9px] text-slate-800 leading-tight">
              <p className="font-bold uppercase tracking-wider">REMARKS / OBSERVATIONS</p>
              <p className="mt-0.5">
                The product has been manufactured and tested in accordance with ASTM A36
                specification and meets all the requirements.
              </p>
              <p className="italic text-slate-600 mt-0.5">
                El producto ha sido fabricado y probado de acuerdo con la especificación ASTM A36 y
                cumple con todos los requisitos.
              </p>
            </div>

            {/* Signatures, Stamps & Validation QR */}
            <div className="pt-2 flex justify-between items-end border-t border-slate-200">
              {/* Signature */}
              <div className="w-36 text-center">
                <div className="font-handwriting text-2xl text-slate-800 h-9 flex items-center justify-center transform -rotate-3">
                  J. Bautist
                </div>
                <div className="border-t border-black pt-1">
                  <p className="font-bold text-[9px]">Quality Assurance</p>
                  <p className="text-[8px] text-slate-600">Control de Calidad</p>
                </div>
              </div>

              {/* Blue Quality Stamp */}
              <div className="relative w-24 h-24 rounded-full border-2 border-blue-700/80 p-1 flex items-center justify-center text-blue-800 transform rotate-[-8deg] opacity-90">
                <div className="w-full h-full rounded-full border border-dashed border-blue-700/80 flex flex-col items-center justify-center p-1 text-center">
                  <span className="text-[7px] font-extrabold uppercase tracking-tight">
                    ACEROS DEL NORTE
                  </span>
                  <div className="w-6 h-6 my-0.5">
                    <svg
                      className="w-full h-full stroke-blue-700 fill-none stroke-[8]"
                      viewBox="0 0 100 100"
                      aria-hidden="true"
                    >
                      <polygon points="50,10 90,90 10,90" />
                      <line x1="50" x2="75" y1="35" y2="90" />
                    </svg>
                  </div>
                  <span className="text-[6.5px] font-bold">S.A. DE C.V.</span>
                </div>
              </div>

              {/* QR Code & Link */}
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 bg-white border border-slate-300 p-1 grid grid-cols-5 gap-0.5">
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-white" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                  <div className="bg-white" />
                  <div className="bg-black" />
                </div>
                <span className="text-[7.5px] text-slate-500 mt-1">www.acerosdelnorte.com</span>
                <span className="text-[7.5px] font-semibold text-slate-800">CERTIFICATE VALID</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* RIGHT PANEL: Data Extraction & Classification Engine                      */}
      {/* ========================================================================= */}
      <main className="flex-1 bg-white flex flex-col min-w-0 overflow-hidden min-h-0">
        {/* Tabs & Action Bar */}
        <div className="h-11 px-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-white">
          <div className="flex space-x-6 h-full text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveTab("extracted")}
              className={`flex items-center h-full px-1 transition-colors ${
                activeTab === "extracted"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Extracted Data
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("validation")}
              className={`flex items-center h-full px-1 transition-colors ${
                activeTab === "validation"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Validation
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("analysis")}
              className={`flex items-center h-full px-1 transition-colors ${
                activeTab === "analysis"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Analysis
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("history")}
              className={`flex items-center h-full px-1 transition-colors ${
                activeTab === "history"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              History
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              className="inline-flex items-center space-x-1.5 px-3 py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded shadow-sm transition"
            >
              <RotateCw className="w-3.5 h-3.5 text-slate-500" />
              <span>Re-extract</span>
            </button>
            <button
              type="button"
              className="p-1 border border-slate-300 rounded hover:bg-slate-50 text-slate-500"
              title="Más acciones"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Form & Analysis Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/60 min-h-0">
          {/* Real-time Import Queue & Processing Status */}
          <ImportQueue items={items} onClearFinished={clearFinished} />

          {/* Section: General Information */}
          <section
            className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm"
            data-purpose="general-information"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-800 text-[13px]">General Information</h3>
              <button
                type="button"
                className="text-xs text-slate-600 hover:text-slate-900 font-medium px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-50"
              >
                Edit
              </button>
            </div>

            <div className="grid grid-cols-2 gap-x-5 gap-y-2.5">
              {/* Left Column of Inputs */}
              <div className="space-y-2">
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Document Type
                  </label>
                  <select
                    defaultValue="Mill Certificate"
                    className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  >
                    <option value="Mill Certificate">Mill Certificate</option>
                    <option value="Commercial Invoice">Commercial Invoice</option>
                    <option value="Packing List">Packing List</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Supplier / Manufacturer
                  </label>
                  <input
                    className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    type="text"
                    defaultValue="ACEROS DEL NORTE S.A. DE C.V."
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Customer
                  </label>
                  <input
                    className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    type="text"
                    defaultValue="INDUSTRIAL SUPPLY S.A. DE C.V."
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Purchase Order
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="PO-45078"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Certificate Number
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="784523"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Date of Issue
                  </label>
                  <div className="relative">
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="2024-02-15"
                    />
                    <Calendar className="w-3.5 h-3.5 absolute right-2.5 top-2.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              {/* Right Column of Inputs */}
              <div className="space-y-2">
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Material
                  </label>
                  <input
                    className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    type="text"
                    defaultValue="Hot Rolled Steel Coil"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Specification / Standard
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="ASTM A36"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Material Grade
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="A36"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Heat / Cast No.
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="H34876"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Lot No.
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="L-230915"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Dimensions
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="3.00 mm x 1,500 mm"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                      Weight (kg)
                    </label>
                    <input
                      className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      type="text"
                      defaultValue="24,580"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                    Country of Origin
                  </label>
                  <select
                    defaultValue="México"
                    className="w-full text-xs font-normal border border-slate-200 rounded px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  >
                    <option value="México">México</option>
                    <option value="United States">United States</option>
                    <option value="Canada">Canada</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          {/* Section: Technical Grids (Chemical & Mechanical) */}
          <div className="grid grid-cols-2 gap-3.5">
            {/* Chemical Composition Grid */}
            <section
              className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
              data-purpose="chemical-composition"
            >
              <div className="flex items-center justify-between mb-2.5">
                <h4 className="font-bold text-slate-800 text-xs">Chemical Composition (%)</h4>
                <button
                  type="button"
                  className="text-[11px] text-slate-600 hover:text-slate-900 px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-50"
                >
                  Edit
                </button>
              </div>

              {/* First Row Elements */}
              <div className="grid grid-cols-6 gap-1 text-center mb-1.5">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">C</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.17"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Mn</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.85"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Si</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.24"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">P</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.012"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">S</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.008"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Cu</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.20"
                  />
                </div>
              </div>

              {/* Second Row Elements */}
              <div className="grid grid-cols-6 gap-1 text-center">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Cr</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.03"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Ni</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.02"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Mo</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.01"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">V</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.002"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-0.5">Al</label>
                  <input
                    className="w-full text-center text-[11px] px-1 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="0.035"
                  />
                </div>
                <div className="opacity-0 pointer-events-none" />
              </div>
            </section>

            {/* Mechanical Properties Grid */}
            <section
              className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
              data-purpose="mechanical-properties"
            >
              <div className="flex items-center justify-between mb-2.5">
                <h4 className="font-bold text-slate-800 text-xs">Mechanical Properties</h4>
                <button
                  type="button"
                  className="text-[11px] text-slate-600 hover:text-slate-900 px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-50"
                >
                  Edit
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-left">
                <div>
                  <label className="text-[10.5px] text-slate-500 block mb-0.5">
                    Yield Strength (MPa)
                  </label>
                  <input
                    className="w-full text-[11px] px-2 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="250"
                  />
                </div>
                <div>
                  <label className="text-[10.5px] text-slate-500 block mb-0.5">
                    Tensile Strength (MPa)
                  </label>
                  <input
                    className="w-full text-[11px] px-2 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="400"
                  />
                </div>
                <div>
                  <label className="text-[10.5px] text-slate-500 block mb-0.5">
                    Elongation (%)
                  </label>
                  <input
                    className="w-full text-[11px] px-2 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="26"
                  />
                </div>
                <div>
                  <label className="text-[10.5px] text-slate-500 block mb-0.5">Hardness (HB)</label>
                  <input
                    className="w-full text-[11px] px-2 py-1 border border-slate-200 rounded bg-slate-50/50"
                    type="text"
                    defaultValue="120"
                  />
                </div>
              </div>
            </section>
          </div>

          {/* Section: Classification Engine (Card) */}
          <section
            className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm"
            data-purpose="classification-engine"
          >
            {/* Header with Match & Confidence */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 rounded bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
                  <FlaskConical className="w-3.5 h-3.5" />
                </div>
                <h4 className="font-bold text-slate-900 text-xs">Classification Engine</h4>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                  Match found
                </span>
              </div>

              {/* Confidence Progress Indicator */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500">
                  Confidence: <strong className="text-slate-800">98.7%</strong>
                </span>
                <div className="w-20 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "98.7%" }} />
                </div>
              </div>
            </div>

            {/* Content Columns: Suggested / Match Details / Risk Indicators */}
            <div className="grid grid-cols-12 gap-4">
              {/* Suggested Classification */}
              <div className="col-span-4 bg-emerald-50/50 border border-emerald-100 rounded-lg p-3 flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-slate-500 block mb-1">
                    Suggested Classification
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-black text-slate-900 tracking-tight font-mono">
                      7208.10.00
                    </span>
                    <span className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-600 mt-2 leading-relaxed">
                    Flat-rolled products of iron or non-alloy steel, of a width of 600 mm or more,
                    hot-rolled, not clad, plated or coated.
                  </p>
                </div>
              </div>

              {/* Match Details Checklist */}
              <div className="col-span-4 space-y-1 text-[11px]">
                <span className="text-[11px] font-bold text-slate-800 block mb-1">Match Details</span>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Material: Carbon steel (ASTM A36)</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Product form: Hot rolled coil</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Dimensions: 3.00 mm x 1,500 mm</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Specification: ASTM A36</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Chemical composition: Within range</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-700">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 stroke-[2.5]" />
                  <span className="truncate">Country of origin: México</span>
                </div>
              </div>

              {/* Risk Indicators */}
              <div className="col-span-4 pl-2 border-l border-slate-100 space-y-1.5 text-[11px]">
                <span className="text-[11px] font-bold text-slate-800 block mb-1">
                  Risk Indicators
                </span>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-slate-600 truncate">
                    <span className="w-2.5 h-2.5 rounded-full border border-slate-300 inline-block" />
                    <span className="truncate">Document authenticity</span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-600 px-1">Valid</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-slate-600 truncate">
                    <span className="w-2.5 h-2.5 rounded-full border border-slate-300 inline-block" />
                    <span className="truncate">Data consistency</span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-600 px-1">Valid</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-slate-600 truncate">
                    <span className="w-2.5 h-2.5 rounded-full border border-slate-300 inline-block" />
                    <span className="truncate">Specification match</span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-600 px-1">Valid</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-slate-600 truncate">
                    <span className="w-2.5 h-2.5 rounded-full border border-slate-300 inline-block" />
                    <span className="truncate">Unusual values</span>
                  </div>
                  <span className="text-[10px] font-normal text-slate-400 px-1">None</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1 text-slate-600 truncate">
                    <span className="w-2.5 h-2.5 rounded-full border border-slate-300 inline-block" />
                    <span className="truncate">Sanctions / restrictions</span>
                  </div>
                  <span className="text-[10px] font-normal text-slate-400 px-1">None</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Bottom Action Bar */}
        <footer className="h-14 bg-white border-t border-slate-200 px-4 flex items-center justify-between shrink-0">
          {/* Comments Input */}
          <div className="relative flex-1 max-w-sm mr-4">
            <MessageSquare className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              className="w-full text-xs pl-8 pr-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white placeholder:text-slate-400 text-slate-700"
              placeholder="Comments (optional)"
              type="text"
            />
          </div>

          {/* Reject & Approve Actions */}
          <div className="flex items-center space-x-2.5">
            {/* Reject Button */}
            <button
              type="button"
              className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-md font-medium text-xs flex items-center space-x-1.5 transition"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject</span>
            </button>

            {/* Approve Button Group */}
            <div className="inline-flex rounded-md shadow-sm">
              <button
                type="button"
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-l-md font-semibold text-xs flex items-center space-x-1.5 transition shadow-sm"
              >
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Approve</span>
              </button>
              <button
                type="button"
                className="px-2 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-r-md border-l border-emerald-500 transition"
                title="Más opciones de aprobación"
              >
                <ChevronDown className="w-3.5 h-3.5 stroke-[2.5]" />
              </button>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
