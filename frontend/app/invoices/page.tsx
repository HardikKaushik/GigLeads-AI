"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Invoice } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function InvoicesPage() {
  const { user } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);

  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [serviceDesc, setServiceDesc] = useState("");
  const [serviceAmount, setServiceAmount] = useState("");
  const [services, setServices] = useState<{ description: string; amount: number }[]>([]);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    api.getInvoices().then(setInvoices).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const addService = () => {
    if (!serviceDesc || !serviceAmount) return;
    setServices([...services, { description: serviceDesc, amount: parseFloat(serviceAmount) }]);
    setServiceDesc(""); setServiceAmount("");
  };

  const createInvoice = async () => {
    if (!clientName || services.length === 0) return;
    setCreating(true);
    try {
      await api.createInvoice({ client_name: clientName, client_email: clientEmail || undefined, services });
      setShowForm(false); setClientName(""); setClientEmail(""); setServices([]);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to create invoice");
    } finally { setCreating(false); }
  };

  const updateStatus = async (id: string, status: string) => {
    try { await api.updateInvoiceStatus(id, status); load(); } catch {}
  };

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="mt-1 text-sm text-gray-500">Create and track invoices</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
          {showForm ? "Cancel" : "New Invoice"}
        </button>
      </div>

      {showForm && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-gray-900">Create Invoice</h2>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Client Name</label>
              <input value={clientName} onChange={(e) => setClientName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" placeholder="Acme Corp" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Client Email</label>
              <input value={clientEmail} onChange={(e) => setClientEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" placeholder="billing@acme.com" />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700">Services</label>
            <div className="mt-2 flex gap-2">
              <input value={serviceDesc} onChange={(e) => setServiceDesc(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Service description" />
              <input value={serviceAmount} onChange={(e) => setServiceAmount(e.target.value)} type="number"
                className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Amount" />
              <button onClick={addService} className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200">Add</button>
            </div>
            {services.length > 0 && (
              <ul className="mt-2 space-y-1">
                {services.map((s, i) => (
                  <li key={i} className="flex justify-between rounded bg-gray-50 px-3 py-1.5 text-sm">
                    <span>{s.description}</span><span className="font-medium">${s.amount.toLocaleString()}</span>
                  </li>
                ))}
                <li className="flex justify-between px-3 py-1.5 text-sm font-bold">
                  <span>Total</span><span>${services.reduce((a, s) => a + s.amount, 0).toLocaleString()}</span>
                </li>
              </ul>
            )}
          </div>
          <button onClick={createInvoice} disabled={creating || !clientName || services.length === 0}
            className="mt-4 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {creating ? "Creating..." : "Create Invoice"}
          </button>
        </div>
      )}

      {loading ? (
        <div className="mt-8 animate-pulse text-gray-400">Loading invoices...</div>
      ) : invoices.length === 0 ? (
        <div className="mt-8 text-center text-gray-400">No invoices yet.</div>
      ) : (
        <div className="mt-6 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Invoice #</th><th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Amount</th><th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Due Date</th><th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{inv.invoice_number}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{inv.client_name}</td>
                  <td className="px-4 py-3 font-semibold">${inv.amount.toLocaleString()}</td>
                  <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                  <td className="px-4 py-3 text-gray-500">{new Date(inv.due_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <select value={inv.status} onChange={(e) => updateStatus(inv.id, e.target.value)}
                      className="rounded border border-gray-200 px-2 py-1 text-xs">
                      {["draft", "sent", "paid", "overdue", "cancelled"].map((s) => (<option key={s} value={s}>{s}</option>))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
