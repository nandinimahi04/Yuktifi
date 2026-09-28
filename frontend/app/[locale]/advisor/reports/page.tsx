"use client";
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Download, FileText, Calendar, Filter, Plus } from 'lucide-react';
import { motion } from 'framer-motion';

const MOCK_REPORTS = [
  { id: 1, name: "Q3 Maharashtra Micro, Small and Medium Enterprises Disbursement Analysis", date: "Oct 1, 2026", size: "2.4 MB", type: "PDF" },
  { id: 2, name: "Solapur Textile Cluster Risk Assessment", date: "Sep 15, 2026", size: "1.1 MB", type: "CSV" },
  { id: 3, name: "NSFDC Default Rate Projection 2027", date: "Sep 01, 2026", size: "3.8 MB", type: "PDF" },
  { id: 4, name: "Rural Women Entrepreneurship Impact", date: "Aug 20, 2026", size: "4.2 MB", type: "PDF" },
];

export default function ReportsPage() {
  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 animate-in fade-in duration-500 font-sans text-warm-text">
      <div className="mb-8 mt-6 flex flex-col md:flex-row justify-between md:items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-warm-text mb-2">Regional Reports</h1>
          <p className="text-warm-muted font-medium text-sm">Aggregated data & Impact analysis & Export</p>
        </div>
        <button className="mt-4 md:mt-0 flex items-center bg-warm-primary hover:bg-orange-600 text-warm-text px-5 py-2.5 text-sm font-bold transition-all rounded-xl shadow-sm">
          <Plus size={18} className="mr-2" /> Generate New Report
        </button>
      </div>

      <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 mb-6">
        <div className="flex-1 relative">
          <input 
            type="text" 
            placeholder="Search reports by keyword..."
            className="w-full px-4 py-3 bg-white border border-warm-border text-warm-text rounded-xl focus:outline-none focus:ring-2 focus:ring-warm-primary focus:border-transparent transition-all shadow-sm"
          />
        </div>
        <button className="flex items-center justify-center px-5 py-3 bg-white border border-warm-border hover:bg-warm-bg transition-colors text-sm font-bold text-warm-muted rounded-xl shadow-sm">
          <Filter size={18} className="mr-2" /> Filter
        </button>
        <button className="flex items-center justify-center px-5 py-3 bg-white border border-warm-border hover:bg-warm-bg transition-colors text-sm font-bold text-warm-muted rounded-xl shadow-sm">
          <Calendar size={18} className="mr-2" /> Date Range
        </button>
      </div>

      <Card className="bg-warm-surface border-warm-border rounded-2xl shadow-sm overflow-hidden">
        <CardHeader className="border-b border-warm-border bg-warm-bg/50 pb-4">
          <CardTitle className="text-warm-text font-bold text-sm uppercase tracking-wider flex items-center">
            <FileText size={18} className="mr-2 text-warm-primary" />
            Available Reports Archive
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-warm-bg/30 text-warm-muted text-xs font-bold uppercase tracking-wider">
                <tr>
                  <th className="p-4 border-b border-warm-border">Report Name</th>
                  <th className="p-4 border-b border-warm-border">Date Generated</th>
                  <th className="p-4 border-b border-warm-border">Format</th>
                  <th className="p-4 border-b border-warm-border">Size</th>
                  <th className="p-4 border-b border-warm-border text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-warm-border text-sm">
                {MOCK_REPORTS.map((report, idx) => (
                  <motion.tr 
                    key={report.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="hover:bg-warm-bg/50 transition-colors group"
                  >
                    <td className="p-4 font-bold flex items-center text-warm-text">
                      <FileText size={18} className="mr-3 text-warm-primary" />
                      <span className="group-hover:text-warm-primary transition-colors">{report.name}</span>
                    </td>
                    <td className="p-4 text-warm-muted font-medium">{report.date}</td>
                    <td className="p-4">
                      <span className="bg-orange-50 text-warm-primary border border-orange-100 px-2.5 py-1 text-xs font-bold rounded-md">
                        {report.type}
                      </span>
                    </td>
                    <td className="p-4 text-warm-muted font-medium">{report.size}</td>
                    <td className="p-4 text-right">
                      <button className="inline-flex items-center text-sm font-bold text-warm-primary hover:text-orange-600 transition-colors">
                        <Download size={16} className="mr-1.5" /> Download
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
