import React from "react";
import { useNavigate, Link } from "react-router-dom";
import avatar from "../../assets/picture/water.png";

const LangdingPage = () => {
  const navigate = useNavigate();
  const handleClick = (value) => {
    navigate(`/login/${value}`);
  };

  return (
    <div className="relative w-screen min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-[#2AF598] to-[#08AEEA]">
      <div className="absolute top-[-10%] left-[-5%] w-1/3 h-1/3 rounded-full bg-white/10 blur-xl"></div>
      <div className="absolute bottom-[-10%] right-[-5%] w-1/2 h-1/2 rounded-full bg-white/10 blur-xl"></div>

      <div className="relative z-10 flex flex-col md:flex-row w-full max-w-5xl mx-auto p-6">
        <div className="w-full md:w-1/2 flex flex-col justify-center items-center md:items-start text-white mb-8 md:mb-0 md:pr-10">
          <div className="flex items-center mb-6">
            <div className="flex font-quicksand font-bold text-4xl">
              <p className="text-[#ffe713]">Smart</p>
              <p className="text-white">Water</p>
            </div>
          </div>

          <div className="hidden md:block mt-10">
            <img
              src={avatar}
              alt="Water Resource"
              className="w-64 h-64 object-cover rounded-full border-4 border-white shadow-2xl"
            />
          </div>
        </div>

        {/* Right side - Card */}
        <div className="w-full md:w-1/2">
          <div className="bg-white rounded-2xl p-8 shadow-[6px_6px_0px_0px_rgba(156,219,166,0.8)] border border-gray-200">
            <div className="flex flex-col items-center">
              <div className="md:hidden mb-8">
                <img
                  src={avatar}
                  alt="Water Resource"
                  className="w-36 h-36 object-cover rounded-full border-4 border-[#0D986A] shadow-lg"
                />
              </div>

              <h2 className="text-[48px] text-[#f0560e] font-semibold font-poppins">
                Đăng nhập
              </h2>
              <p className="text-[24px] font-semibold text-black/60 mb-8">
                với tư cách
              </p>

              <div className="w-full space-y-5 mb-8">
                <button
                  onClick={() => handleClick("customer")}
                  className="w-full py-4 px-6 bg-white border-2 border-[#0D986A] text-[#0D986A] rounded-2xl
                  text-lg font-medium hover:bg-green-50 transition-all duration-300
                  shadow-[0px_4px_10px_rgba(13,152,106,0.2)] hover:shadow-[0px_6px_15px_rgba(13,152,106,0.3)]"
                >
                  Khách hàng
                </button>

                <button
                  onClick={() => handleClick("admin")}
                  className="w-full py-4 px-6 bg-[#0D986A] text-white rounded-2xl
                  text-lg font-medium hover:bg-[#0B8459] transition-all duration-300
                  shadow-[0px_8px_28px_0px_rgba(79,117,105,0.5)] hover:shadow-[0px_8px_28px_0px_rgba(79,117,105,0.7)]"
                >
                  Quản trị viên
                </button>
              </div>

              <Link
                to="/register"
                className="text-[17px] font-medium bg-gradient-to-t from-[#013220] to-[#016734] 
                bg-clip-text text-transparent hover:underline decoration-[#013220]"
              >
                Yêu cầu đăng ký tài khoản!
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LangdingPage;
