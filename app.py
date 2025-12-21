import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış Yönetim Sistemi Pro", page_icon="🏢", layout="wide")

# --- SESSION STATE (GEÇİCİ HAFIZA) ---
if 'sepet' not in st.session_state:
    st.session_state.sepet = []

# --- GÜVENLİK VE BAĞLANTI ---
def check_password():
    """Kullanıcı girişini kontrol eder."""
    def password_entered():
        if (st.session_state["username"] in st.secrets["users"] and 
            st.session_state["password"] == st.secrets["users"][st.session_state["username"]]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Kullanıcı Adı", key="login_user")
        st.text_input("Şifre", type="password", key="login_pass")
        st.button("Giriş Yap", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Kullanıcı Adı", key="login_user_retry")
        st.text_input("Şifre", type="password", key="login_pass_retry")
        st.button("Giriş Yap", on_click=password_entered)
        st.error("😕 Hatalı giriş.")
        return False
    else:
        return True

def get_google_sheet_client():
    """Google Sheets bağlantısını kurar."""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- PROFESYONEL MAİL GÖNDERME (SSL DÜZELTİLMİŞ) ---
def mail_gonder_generic(alici_email, konu, html_icerik):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["server"]
        smtp_port = st.secrets["email"]["port"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Satis Departmani <{sender_email}>"
        msg['To'] = alici_email
        msg['Subject'] = konu

        msg.attach(MIMEText(html_icerik, 'html'))

        # SSL Context (Güvenlik Duvarını Aşmak İçin - Port 465 Özel)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4 
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, alici_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail hatası: {e}")
        return False

def olustur_profesyonel_teklif_maili(musteri_adi, sepet, ara_toplam, iskonto_orani, iskonto_tutari, kdv_orani, kdv_tutari, genel_toplam, para_birimi, notlar):
    """Çoklu ürün içeren mail şablonu."""
    satirlar_html = ""
    for urun in sepet:
        satirlar_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{urun['Urun']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{urun['Adet']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{urun['Birim Fiyat']:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{urun['Toplam']:,.2f}</td>
        </tr>
        """

    html = f"""
    <html>
      <body style="font-family: sans-serif; color: #333; padding: 20px;">
        <div style="border: 1px solid #ddd; padding: 20px; max-width: 700px; margin: auto;">
            <h2 style="color: #2c3e50;">Fiyat Teklifi</h2>
            <p>Sayın <b>{musteri_adi}</b> Yetkilisi,</p>
            <p>Talebiniz üzerine hazırlanan teklif detayları aşağıdadır:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; text-align: left;">Ürün</th>
                        <th style="padding: 8px; text-align: center;">Adet</th>
                        <th style="padding: 8px; text-align: right;">Fiyat</th>
                        <th style="padding: 8px; text-align: right;">Tutar</th>
                    </tr>
                </thead>
                <tbody>{satirlar_html}</tbody>
            </table>
            
            <div style="margin-top: 20px; text-align: right;">
                <p><b>Ara Toplam:</b> {ara_toplam:,.2f} {para_birimi}</p>
                <p style="color: red;"><b>İskonto (%{iskonto_orani}):</b> -{iskonto_tutari:,.2f} {para_birimi}</p>
                <p><b>KDV (%{kdv_orani}):</b> +{kdv_tutari:,.2f} {para_birimi}</p>
                <h3>GENEL TOPLAM: {genel_toplam:,.2f} {para_birimi}</h3>
            </div>
            
            <hr>
            <p><b>Notlar:</b> {notlar}</p>
            <p style="font-size: 12px; color: #777;">Bu mail otomatik oluşturulmuştur.</p>
        </div>
      </body>
    </html>
    """
    return html

# --- ANA UYGULAMA ---
if check_password():
    st.sidebar.title("Satış Paneli")
    menu = st.sidebar.radio("Modül Seçiniz:", ["📍 Ziyaret Girişi", "💰 Profesyonel Teklif", "📋 Fiyat Listesi", "📊 Patron Ekranı"])

    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
    except:
        st.error("Veritabanı bağlantı hatası. 'Satis_Raporlari' dosyası bulunamadı.")
        st.stop()

    # --- 1. MODÜL: ZİYARET GİRİŞİ ---
    if menu == "📍 Ziyaret Girişi":
        st.header("📍 Ziyaret Raporu")
        ws_ziyaret = sh.worksheet("Ziyaretler")
        
        with st.form("ziyaret_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                tarih = st.date_input("Tarih", datetime.today())
                firma = st.text_input("Firma Adı")
            with c2:
                kisi = st.text_input("Görüşülen Kişi")
                email = st.text_input("E-Posta")
            with c3:
                durum = st.selectbox("Durum", ["Tanışma", "Teklif", "Sıcak Satış", "Satış Kapandı"])
                urunler = st.multiselect("Ürünler", ["Rulman", "ZKL", "Kinex", "Sensimore", "Hizmet"])
                potansiyel = st.number_input("Potansiyel (TL)", step=1000)

            notlar = st.text_area("Notlar")
            mail_at = st.checkbox("Teşekkür Maili Gönder")
            if st.form_submit_button("Kaydet"):
                # Çift Durum sütunu hatasını önlemek için boşlukları temizleyerek gönderiyoruz
                ws_ziyaret.append_row([str(tarih), firma, "", kisi, "", email, durum, ", ".join(urunler), potansiyel, "", "", "", "", notlar, str(datetime.now())])
                st.success("Kaydedildi.")
                if mail_at and email:
                    mail_gonder_generic(email, f"Ziyaret Hk. - {firma}", f"Sayın {kisi}, ziyaretiniz için teşekkürler.")
                    st.success("Mail gönderildi.")

    # --- 2. MODÜL: PROFESYONEL TEKLİF ROBOTU ---
    elif menu == "💰 Profesyonel Teklif":
        st.header("💰 Çoklu Ürün Teklif Robotu")
        
        try:
            ws_fiyat = sh.worksheet("Fiyat_Listesi")
            ws_teklif = sh.worksheet("Teklifler")
            ws_ziyaret = sh.worksheet("Ziyaretler")
            
            df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
            df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
            
            musteri_listesi = ["➕ Yeni Müşteri"]
            mail_sozlugu = {}
            
            if not df_ziyaret.empty:
                df_ziyaret.columns = df_ziyaret.columns.str.strip()
                if "Firma Adı" in df_ziyaret.columns:
                    firmalar = [x for x in df_ziyaret["Firma Adı"].unique() if x]
                    firmalar.sort()
                    musteri_listesi += firmalar
                if "Firma Adı" in df_ziyaret.columns and "E-Posta" in df_ziyaret.columns:
                     for i, row in df_ziyaret.iterrows():
                        if row["Firma Adı"]: mail_sozlugu[row["Firma Adı"]] = str(row["E-Posta"])

        except Exception as e:
            st.error(f"Veri hatası: {e}")
            st.stop()

        # --- A. ÜST BİLGİLER ---
        col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
        with col_m1:
            secilen_musteri = st.selectbox("Müşteri Seçiniz", musteri_listesi, key="teklif_musteri")
            if secilen_musteri == "➕ Yeni Müşteri":
                final_musteri = st.text_input("Müşteri Ünvanı Giriniz", key="teklif_yeni_musteri_input")
                otomatik_mail = ""
            else:
                final_musteri = secilen_musteri
                otomatik_mail = mail_sozlugu.get(final_musteri, "")
        
        with col_m2:
            teklif_tarihi = st.date_input("Tarih", datetime.today(), key="teklif_tarih")
        with col_m3:
            # Benzersiz KEY eklendi:
            para_birimi = st.selectbox("Para Birimi", ["TL", "USD", "EUR"], key="teklif_para_birimi")

        # --- B. ÜRÜN EKLEME ALANI ---
        st.markdown("---")
        st.subheader("🛒 Ürün Ekle")
        
        col_u1, col_u2, col_u3, col_u4 = st.columns([3, 1, 1, 1])
        urun_etiketleri = [""] + (df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else [])
        
        with col_u1:
            secilen_urun_liste = st.selectbox("Listeden Ürün Seç", urun_etiketleri, key="teklif_urun_secimi")
            otomatik_fiyat = 0.0
            manuel_urun_adi = ""
            if secilen_urun_liste and not df_fiyat.empty:
                satir = df_fiyat[df_fiyat['Urun Adi'] == secilen_urun_liste].iloc[0]
                try:
                    otomatik_fiyat = float(str(satir['Birim Fiyat']).replace(",","."))
                except:
                    otomatik_fiyat = 0.0
                manuel_urun_adi = secilen_urun_liste

            final_urun_adi = st.text_input("Ürün Adı (Düzenlenebilir)", value=manuel_urun_adi, key="teklif_urun_adi_input")

        with col_u2:
            adet = st.number_input("Adet", min_value=1, value=1, key="teklif_adet")
        with col_u3:
            birim_fiyat = st.number_input("Birim Fiyat", value=otomatik_fiyat, min_value=0.0, format="%.2f", key="teklif_birim_fiyat")
        with col_u4:
            st.write("##")
            if st.button("➕ Listeye Ekle", type="primary", key="teklif_ekle_btn"):
                if final_urun_adi:
                    tutar = adet * birim_fiyat
                    st.session_state.sepet.append({
                        "Urun": final_urun_adi,
                        "Adet": adet,
                        "Birim Fiyat": birim_fiyat,
                        "Toplam": tutar
                    })
                    st.success("Eklendi")
                else:
                    st.warning("Ürün adı boş olamaz")

        # --- C. SEPET LİSTESİ ---
        if st.session_state.sepet:
            st.markdown("### 📋 Teklif İçeriği")
            df_sepet = pd.DataFrame(st.session_state.sepet)
            st.table(df_sepet)
            
            col_sil, _ = st.columns([1, 4])
            with col_sil:
                silinecek_index = st.number_input("Silinecek Sıra No", min_value=0, max_value=len(st.session_state.sepet)-1, step=1, key="sil_index")
                if st.button("🗑️ Sil", key="sil_btn"):
                    st.session_state.sepet.pop(silinecek_index)
                    st.rerun()

            # --- D. HESAPLAMALAR ---
            st.markdown("---")
            c_calc1, c_calc2, c_calc3 = st.columns(3)
            ara_toplam = sum(item['Toplam'] for item in st.session_state.sepet)
            
            with c_calc1:
                iskonto_orani = st.number_input("İskonto (%)", 0.0, 100.0, 0.0, key="iskonto_input")
                iskonto_tutari = ara_toplam * (iskonto_orani / 100)
                
            with c_calc2:
                kdv_orani = st.number_input("KDV (%)", 0.0, 100.0, 20.0, key="kdv_input")
                matrah = ara_toplam - iskonto_tutari
                kdv_tutari = matrah * (kdv_orani / 100)

            genel_toplam = matrah + kdv_tutari
            
            with c_calc3:
                st.metric("Genel Toplam", f"{genel_toplam:,.2f} {para_birimi}")

            # --- E. KAYDET ---
            st.markdown("---")
            col_mail, col_btn = st.columns([2, 1])
            with col_mail:
                teklif_mail = st.text_input("Alıcı E-Posta", value=otomatik_mail, key="teklif_alici_mail")
                notlar = st.text_area("Notlar", "Ödeme peşin.", key="teklif_notlar")
            
            with col_btn:
                st.write("##")
                mail_gonderilsin = st.checkbox("Mail Gönder", value=True, key="mail_chk")
                
                if st.button("✅ Kaydet", type="primary", use_container_width=True, key="teklif_tamamla_btn"):
                    if final_musteri:
                        urun_ozeti = f"{len(st.session_state.sepet)} Kalem: " + ", ".join([item['Urun'] for item in st.session_state.sepet])
                        ws_teklif.append_row([
                            str(teklif_tarihi), final_musteri, urun_ozeti, 
                            "1", genel_toplam, genel_toplam, "Beklemede", para_birimi
                        ])
                        st.success("Kaydedildi!")
                        
                        if mail_gonderilsin and teklif_mail:
                            with st.spinner("Mail gönderiliyor..."):
                                html_body = olustur_profesyonel_teklif_maili(
                                    final_musteri, st.session_state.sepet, 
                                    ara_toplam, iskonto_orani, iskonto_tutari, 
                                    kdv_orani, kdv_tutari, genel_toplam, para_birimi, notlar
                                )
                                mail_gonder_generic(teklif_mail, f"Fiyat Teklifi - {final_musteri}", html_body)
                                st.success("Mail gönderildi!")
                                st.session_state.sepet = []
                    else:
                        st.error("Müşteri seçiniz.")

    # --- 3. MODÜL: FİYAT LİSTESİ ---
    elif menu == "📋 Fiyat Listesi":
        st.header("📋 Ürün Fiyatları")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        df = pd.DataFrame(ws_fiyat.get_all_records())
        st.dataframe(df, use_container_width=True)
        
        with st.expander("Yeni Ürün Tanımla"):
            c1, c2, c3, c4 = st.columns(4)
            kod = c1.text_input("Kod", key="yeni_urun_kod")
            ad = c2.text_input("Ad", key="yeni_urun_ad")
            fiyat = c3.number_input("Fiyat", key="yeni_urun_fiyat")
            # Benzersiz KEY eklendi:
            para = c4.selectbox("Birim", ["TL", "USD", "EUR"], key="yeni_urun_para")
            if st.button("Ekle", key="yeni_urun_ekle_btn"):
                ws_fiyat.append_row([kod, ad, fiyat, para])
                st.success("Eklendi.")

    # --- 4. MODÜL: DASHBOARD ---
    elif menu == "📊 Patron Ekranı":
        st.header("📊 Satış Özeti")
        try:
            df_teklif = pd.DataFrame(sh.worksheet("Teklifler").get_all_records())
            if not df_teklif.empty: df_teklif.columns = df_teklif.columns.str.strip()
        except:
            st.stop()

        if not df_teklif.empty:
            if "Toplam Tutar" in df_teklif.columns:
                 df_teklif['Toplam Tutar'] = pd.to_numeric(df_teklif['Toplam Tutar'], errors='coerce').fillna(0)
                 toplam_ciro = df_teklif['Toplam Tutar'].sum()
                 st.metric("Toplam Teklif Değeri", f"{toplam_ciro:,.0f}")
            
            if "Durum" in df_teklif.columns:
                fig = px.pie(df_teklif, names='Durum', title='Teklif Durumları')
                st.plotly_chart(fig)
            
            st.subheader("Son Teklifler")
            st.dataframe(df_teklif.tail(10))
