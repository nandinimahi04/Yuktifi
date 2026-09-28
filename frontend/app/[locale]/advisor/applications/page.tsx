"use client";
import React from 'react';
import Link from 'next/link';
import { Search, Filter, ShieldCheck, Clock, CheckCircle2 } from 'lucide-react';
import { YuktiFiInsight } from '@/components/YuktiFiInsight';

const dummyApplications = [
  { id: "APP-001", name: "Rajesh Kumar", business: "Textile Manufacturing", location: "Nagpur Zone A", req: "₹15 Lakhs", score: 88, readiness: 100, status: "Ready for Review", time: "2 hrs ago" },
  { id: "APP-002", name: "Sunita Devi", business: "Organic Farming", location: "Pune Outskirts", req: "₹5 Lakhs", score: 92, readiness: 100, status: "Ready for Review", time: "5 hrs ago" },
  { id: "APP-003", name: "Amit Shah", business: "Retail Electronics", location: "Mumbai North", req: "₹25 Lakhs", score: 65, readiness: 60, status: "Missing Docs", time: "1 day ago" },
  { id: "APP-004", name: "Priya Patel", business: "IT Services", location: "Nashik Central", req: "₹10 Lakhs", score: 78, readiness: 85, status: "In Progress", time: "2 days ago" },
];

export default function ApplicationQueue() {
  const exportToCSV = () => {
    const headers = ["ID", "Name", "Business", "Location", "Capital Requested", "Score", "Readiness %", "Status", "Time"];
    const rows = dummyApplications.map(app => 
      [app.id, app.name, app.business, app.location, app.req, app.score, app.readiness, app.status, app.time].map(val => `"${val}"`).join(",")
    );
    const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "yukti_applications_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-4 md:p-8 bg-warm-bg min-h-screen text-warm-text font-sans animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-warm-border pb-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-warm-text">Review Queue</h1>
          <p className="text-sm font-medium text-warm-muted mt-1">Incoming Business Plans</p>
        </div>
        
        <div className="flex space-x-3 mt-4 md:mt-0">
          <div className="bg-white border border-warm-border flex items-center px-4 py-2 rounded-xl shadow-sm">
            <Search size={16} className="text-warm-muted mr-2" />
            <input type="text" placeholder="Search ID..." className="bg-transparent border-none outline-none text-sm text-warm-text placeholder-warm-muted w-32" />
          </div>
          <button 
            onClick={exportToCSV}
            className="bg-white border border-warm-border hover:bg-orange-50 px-4 py-2 flex items-center text-sm font-bold text-warm-primary transition-colors rounded-xl shadow-sm"
          >
            <Filter size={16} className="mr-2" /> Export CSV
          </button>
        </div>
      </div>

      <YuktiFiInsight 
        type="positive"
        title="QUEUE STATUS"
        message="2 applications have achieved 100% readiness and passed the YuktiFi viability threshold. They are ready for immediate officer review."
        className="mb-6 shadow-sm"
      />

      <div className="overflow-x-auto bg-white rounded-2xl border border-warm-border shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-warm-border bg-warm-bg/50">
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">App ID</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">Applicant & Business</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">Capital Req</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">YuktiFi Score</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">Readiness</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">Status</th>
              <th className="p-4 text-xs font-bold text-warm-muted uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody>
            {dummyApplications.map((app, i) => (
              <tr key={i} className="border-b border-warm-border last:border-0 hover:bg-warm-bg/30 transition-colors group">
                <td className="p-4 font-bold text-sm text-warm-primary">{app.id}</td>
                <td className="p-4">
                  <div className="text-warm-text font-bold text-sm">{app.name}</div>
                  <div className="text-xs font-medium text-warm-muted mt-1">{app.business} • {app.location}</div>
                </td>
                <td className="p-4 text-sm font-medium">{app.req}</td>
                <td className="p-4">
                  <div className={`text-xl font-black ${app.score > 80 ? 'text-emerald-600' : app.score > 70 ? 'text-amber-500' : 'text-red-500'}`}>
                    {app.score}
                  </div>
                </td>
                <td className="p-4">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-bold text-warm-text w-10">{app.readiness}%</span>
                    <div className="w-20 h-2 bg-warm-border rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${app.readiness === 100 ? 'bg-emerald-500' : 'bg-amber-500'}`} 
                        style={{ width: `${app.readiness}%` }}
                      ></div>
                    </div>
                  </div>
                </td>
                <td className="p-4">
                  <div className="flex items-center text-xs font-bold text-warm-muted">
                    {app.readiness === 100 ? (
                      <CheckCircle2 size={16} className="text-emerald-500 mr-2" />
                    ) : (
                      <Clock size={16} className="text-amber-500 mr-2" />
                    )}
                    {app.status}
                  </div>
                </td>
                <td className="p-4">
                  <Link 
                    href={`/advisor/applications/${app.id.toLowerCase()}`}
                    className={`px-4 py-2.5 text-xs font-bold rounded-xl border transition-all flex items-center justify-center w-28 shadow-sm ${
                      app.readiness === 100 
                        ? 'bg-warm-primary border-warm-primary text-warm-text hover:bg-orange-600' 
                        : 'bg-white border-warm-border text-warm-muted hover:border-warm-muted hover:text-warm-text'
                    }`}
                  >
                    <ShieldCheck size={16} className="mr-2" /> Review
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
