import { useState } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../store/wechat";
import { useWeChatAuth } from "../hooks/useWeChatAuth";
import { api } from "../services/api";

interface WeChatLoginButtonProps {
  variant?: "default" | "outline" | "text";
  size?: "sm" | "md" | "lg";
  className?: string;
  onLoginStart?: () => void;
  onLoginError?: (error: string) => void;
}

export function WeChatLoginButton({
  variant = "default",
  size = "md",
  className = "",
  onLoginStart,
  onLoginError,
}: WeChatLoginButtonProps) {
  const router = useRouter();
  const { isWeChatLogged, wechatUser } = useWeChatStore();
  const { logout } = useWeChatAuth();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (isWeChatLogged) {
      // If logged in, show logout option or redirect to accounts
      router.push("/wechat/accounts");
                                                                                                                                      et("/api/wechat/auth/start");
      const {      const {      const {      const {      conur      const {      const {      const {      const {ogin      const {      const {      constn.href = login_url;
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || err.message || "Login failed";
      onLoginError?.(erro      onLoginError?.(erro      onLogi
  };

                                   es                -3 py-1 text-sm",
                    ex              g: "px-6 py-3 text-lg",
  };

  // Variant classes
  const variantClasses = {  const variantClasses = {  const variantClasses = {  cto-e  const variantClasses = {  const vove  const variantClasses = {  const variantClass  ou  const variantClasses = {  const al  const variantCld-400 hov  const variantClasses = {  const variantClasses = {  const vari h  const variantClasses = {  const var
  };

  if (isWeChatLogged && wechatUser) {
    return (
      <div className="flex items-center gap-2">
        {wechatUser.avatar && (
          <img
            src={wechatUser.avatar}
            alt={wechatUser.nickname}
            className="w-8 h-8 rounded-full"
          />
        )}
        <div className="flex flex-col">
                            -sm                  t-whi                            -sm                  t-whi             /p                            -sm                  t-whi       classNam                            -sm                  t-whi                    >
            Logout
          </button>
        </div>
      </div>
    );
  }

  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  r  renter justify-center gap-2
        ${className}
      `}
    >
      {loadi      {loadi      {loadi      {loadi      {lw-4       {loadi      {loadi   0 border-t-white rou      {loadi      {loadi      {loa        {loadi      {loadi      {l    </>
      ) : (
        <>
          <svg class          <-5  fill="cur          <svg class          <-5  fil      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.          11zm3.5 6          <s31-1.46         H6.89c.         78 3   5.11 3.5z" />
          </svg>
          <span>登录 WeChat</span>
        </>
      )}
    </button>
  );
}
