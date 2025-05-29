import React from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";

const About = () => {
  return (
    <div>
      <Header />
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-center mb-4">
          About Smart Water
        </h1>
        <p className="text-center mb-4">
          Smart Water is a project aimed at providing innovative solutions for
          water management and conservation. Our goal is to leverage technology
          to ensure sustainable water usage and to address the challenges of
          water scarcity.
        </p>
        <p className="text-center mb-4">
          Our team consists of experts in the fields of water management,
          environmental science, and technology. We are committed to developing
          smart systems that monitor and manage water resources efficiently.
        </p>
        <p className="text-center mb-4">
          For more information, please contact us at{" "}
          <a
            href="mailto:info@smartwater.com"
            className="text-blue-500 hover:underline"
          >
            info@smartwater.com
          </a>
          .
        </p>
      </div>
      <Footer />
    </div>
  );
};

export default About;
