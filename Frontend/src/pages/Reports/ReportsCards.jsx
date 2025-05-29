import React from "react";

const ReportsCard = ({ report }) => {
  return (
    <div className="bg-amber-50 shadow-md rounded-lg p-6 mt-8">
      <h3 className="text-xl font-semibold text-gray-800 mb-4">
        Chi tiết Báo cáo
      </h3>
      <p className="text-lg text-gray-700">
        <strong>ID:</strong> {report.id}
      </p>
      <p className="text-lg text-gray-700">
        <strong>Tên báo cáo:</strong> {report.name}
      </p>
      <p className="text-lg text-gray-700">
        <strong>Trạng thái:</strong> {report.status}
      </p>
      <p className="text-lg text-gray-700">
        <strong>Ngày:</strong> {report.date}
      </p>
    </div>
  );
};

export default ReportsCard;
