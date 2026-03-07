import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Check, X } from 'lucide-react';
import api from '../api/client';
import { Invoice, Client } from '../types';

export default function Invoices() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadClientId, setUploadClientId] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewData, setReviewData] = useState<Partial<Invoice>>({});
  const [reviewInvoiceId, setReviewInvoiceId] = useState<number | null>(null);

  const fetchData = async () => {
    try {
      const [invRes, cliRes] = await Promise.all([
        api.get('/invoices'),
        api.get('/clients')
      ]);
      setInvoices(invRes.data);
      setClients(cliRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setUploadFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1
  });

  const handleUpload = async () => {
    if (!uploadFile || !uploadClientId) return;
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('client_id', uploadClientId);

    try {
      const res = await api.post('/invoices/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setIsUploadModalOpen(false);
      setUploadFile(null);
      setUploadClientId('');
      
      // Open review modal with AI extracted data
      setReviewData(res.data);
      setReviewInvoiceId(res.data.id);
      setReviewModalOpen(true);
      
    } catch (err) {
      console.error(err);
    }
  };

  const handleReviewSave = async () => {
    if (!reviewInvoiceId) return;
    try {
      await api.put(`/invoices/${reviewInvoiceId}`, reviewData);
      setReviewModalOpen(false);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Facturas</h1>
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-md flex items-center text-sm font-medium"
        >
          <Upload className="w-4 h-4 mr-2" />
          Subir Factura
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-950">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Cliente</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Número</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Fecha</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Total</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Estado</th>
            </tr>
          </thead>
          <tbody className="bg-slate-900 divide-y divide-slate-800">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-400">Cargando...</td></tr>
            ) : invoices.map((inv) => {
              const client = clients.find(c => c.id === inv.client_id);
              return (
                <tr key={inv.id} className="hover:bg-slate-800/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{client?.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{inv.invoice_number || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{inv.invoice_date || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">€{inv.total_amount}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      inv.status === 'paid' ? 'bg-green-100 text-green-800' :
                      inv.status === 'pending' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {inv.status}
                    </span>
                  </td>
                </tr>
              );
            })}
            {!loading && invoices.length === 0 && (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-400">No hay facturas.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={() => setIsUploadModalOpen(false)}>
              <div className="absolute inset-0 bg-slate-950 opacity-75"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-slate-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full border border-slate-800">
              <div className="bg-slate-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg leading-6 font-medium text-white mb-4">Subir Factura</h3>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-300 mb-1">Cliente</label>
                  <select value={uploadClientId} onChange={e => setUploadClientId(e.target.value)} className="block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white">
                    <option value="">Seleccione un cliente...</option>
                    {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>

                <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${isDragActive ? 'border-brand-500 bg-brand-500/10' : 'border-slate-700 hover:border-brand-400 bg-slate-800/50'}`}>
                  <input {...getInputProps()} />
                  <FileText className="mx-auto h-12 w-12 text-slate-400 mb-2" />
                  {uploadFile ? (
                    <p className="text-brand-400 font-medium">{uploadFile.name}</p>
                  ) : (
                    <p className="text-slate-400">Arrastra un PDF aquí, o haz clic para seleccionar</p>
                  )}
                </div>
              </div>
              <div className="bg-slate-950 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-slate-800">
                <button onClick={handleUpload} disabled={!uploadFile || !uploadClientId} className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-brand-600 text-base font-medium text-white hover:bg-brand-700 disabled:opacity-50 sm:ml-3 sm:w-auto sm:text-sm">
                  Procesar con IA
                </button>
                <button onClick={() => setIsUploadModalOpen(false)} className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-700 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-300 hover:bg-slate-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {reviewModalOpen && (
        <div className="fixed z-20 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-slate-950 opacity-90"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-slate-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full border border-brand-500/50">
              <div className="bg-slate-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg leading-6 font-medium text-white">Revisión de IA</h3>
                  {reviewData.ai_confidence && (
                    <span className="bg-brand-500/20 text-brand-400 px-2 py-1 rounded text-xs font-semibold">
                      Confianza: {(reviewData.ai_confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Número de Factura</label>
                    <input type="text" value={reviewData.invoice_number || ''} onChange={e => setReviewData({...reviewData, invoice_number: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Fecha</label>
                    <input type="date" value={reviewData.invoice_date || ''} onChange={e => setReviewData({...reviewData, invoice_date: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Subtotal (€)</label>
                    <input type="number" step="0.01" value={reviewData.amount || ''} onChange={e => setReviewData({...reviewData, amount: parseFloat(e.target.value)})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Impuestos (€)</label>
                    <input type="number" step="0.01" value={reviewData.tax_amount || ''} onChange={e => setReviewData({...reviewData, tax_amount: parseFloat(e.target.value)})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Total (€)</label>
                    <input type="number" step="0.01" value={reviewData.total_amount || ''} onChange={e => setReviewData({...reviewData, total_amount: parseFloat(e.target.value)})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400">Estado</label>
                    <select value={reviewData.status || 'pending'} onChange={e => setReviewData({...reviewData, status: e.target.value as any})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white">
                      <option value="pending">Pendiente</option>
                      <option value="paid">Pagada</option>
                      <option value="overdue">Vencida</option>
                    </select>
                  </div>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium text-slate-400">Concepto / Descripción</label>
                  <textarea value={reviewData.concept || ''} onChange={e => setReviewData({...reviewData, concept: e.target.value})} rows={3} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                </div>
              </div>
              <div className="bg-slate-950 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-slate-800">
                <button onClick={handleReviewSave} className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 sm:ml-3 sm:w-auto sm:text-sm">
                  <Check className="w-4 h-4 mr-2" />
                  Confirmar y Guardar
                </button>
                <button onClick={() => setReviewModalOpen(false)} className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-700 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-300 hover:bg-slate-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                  <X className="w-4 h-4 mr-2" />
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
