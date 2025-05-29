import React from "react";
import logo from "../assets/picture/water.png";
import { FaFacebook, FaTwitter, FaLinkedin } from "react-icons/fa";

const Footer = () => {
  return (
    <footer className="bg-gray-700 text-white py-4">
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row justify-between items-center">
          <div className="flex items-center mb-3 sm:mb-0">
            <img src={logo} alt="HCMUT Logo" className="h-10 mr-3" />
            <p className="text-lg font-bold">Smart Water</p>
          </div>

          <div className="flex space-x-4 mb-3 sm:mb-0">
            <a href="#" className="text-gray-300 hover:text-blue-400">
              <FaFacebook size={20} />
            </a>
            <a href="#" className="text-gray-300 hover:text-blue-400">
              <FaTwitter size={20} />
            </a>
            <a href="#" className="text-gray-300 hover:text-blue-400">
              <FaLinkedin size={20} />
            </a>
          </div>

          <nav>
            <ul className="flex space-x-4 text-xs">
              <li>
                <a
                  href="/privacy"
                  className="text-gray-300 hover:text-blue-300"
                >
                  Privacy
                </a>
              </li>
              <li>
                <a href="/terms" className="text-gray-300 hover:text-blue-300">
                  Terms
                </a>
              </li>
              <li>
                <a
                  href="/contact"
                  className="text-gray-300 hover:text-blue-300"
                >
                  Contact
                </a>
              </li>
            </ul>
          </nav>
        </div>

        {/* Copyright */}
        <div className="text-center text-xs text-gray-400 mt-2">
          &copy; 2025 Smart Water. All rights reserved.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
