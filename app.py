import streamlit as st
import pandas as pd
from io import BytesIO
import datetime
import os

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Rulman Fiyat Listesi", layout="centered")

st.title("🔩 Satış Teklif Robotu")

# --- 0. Sepet (Session State) Kurulumu ---
# Program hafızasında bir sepet oluşturuyoruz. Sayfa yenilense bile silinmez.
if 'sepet' not in st.session_state:
    st.session_state['sepet'] = pd.DataFrame(columns=['Urun_Kodu', 'Urun_Adi', 'Liste_Fiyati', 'Adet', 'Secim_Ismi'])

# --- 1. Veri Yükleme (OTOMATİK) ---
SABIT_DOSYA_ADI = "fiyatlar.xlsx"

@st.cache_data
def load_data_from_repo():
    if not os.path.exists(SABIT_DOSYA_ADI):
        return None, f"HATA: '{SABIT_DOSYA_ADI}' dosyası bulunamadı."
    
    try:
        df = pd.read_excel(SABIT_DOSYA_ADI)
        if 'Urun_Kodu' not in df.columns:
            df = pd.read_excel(SABIT_DOSYA_ADI, header=1)
        if 'Urun_Kodu' not in df.columns:
            return None, "HATA: 'Urun_Kodu' başlığı bulunamadı."

        df.columns = df.columns.str.strip()
        
        # Fiyat temizliği
        fiyat_col = [col for col in df.columns if 'Fiyat' in col]
        if fiyat_col:
            col_name = fiyat_col[0]
            def clean_price_fast(val):
                if pd.isna(val): return 0.0
                if isinstance(val, (int, float)): return float(val)
                s = str(val)
                if "#" in s: return 0.0
                s = s.replace('€', '').replace('TL', '').replace('$', '').strip()
                if "." in s and "," in s: s = s.replace('.', '').replace(',', '.')
                elif "," in s: s = s.replace(',', '.')
                try: return float(s)
                except: return 0.0
            df[col_name] = df[col_name].apply(clean_price_fast)
            df.rename(columns={col_name: 'Fiyat'}, inplace=True)
        
        df['Urun_Kodu'] = df['Urun_Kodu'].astype(str)
        df['Urun_Adi'] = df['Urun_Adi'].astype(str)
        df = df.drop_duplicates()
        # Benzersiz İsim Oluştur
        df['Secim_Ismi'] = df['Urun_Kodu'] + " - " + df['Urun_Adi'] + " (" + df['Fiyat'].apply(lambda x: f"{x:.2f}") + " €)"
        
        return df, None
    except Exception as e:
        return None, f"Dosya okuma hatası: {e}"

df, error_msg = load_data_from_repo()

if error_msg:
    st.error(error_msg)
elif df is not None:
    # --- 2. Ürün Ekleme Alanı ---
    st.subheader("1. Ürün Ekle")
    
    col_ara, col_ekle = st.columns([3, 1])
    
    with col_ara:
        arama_kelimesi = st.text_input("Ürün Ara:", placeholder="Örn: 6205")
        
        df_clean = df[df['Fiyat'] > 0]
        filtrelenmis_df = df_clean.head(0)

        if arama_kelimesi:
            mask = (
                df_clean['Urun_Kodu'].str.contains(arama_kelimesi, case=False, na=False) | 
                df_clean['Urun_Adi'].str.contains(arama_kelimesi, case=False, na=False)
            )
            filtrelenmis_df = df_clean[mask]
        
        secenekler = filtrelenmis_df['Secim_Ismi'].tolist()
        
        # Seçim Kutusu (Burada seçip butona basacaksın)
        secilen_yeni_urunler = st.multiselect("Listeden Seçiniz:", options=secenekler, key="urun_secici")

    with col_ekle:
        st.write("") # Boşluk
        st.write("") # Boşluk
        if st.button("➕ Listeye Ekle", type="primary"):
            if secilen_yeni_urunler:
                # Seçilenleri ana veriden bul
                yeni_df = df_clean[df_clean['Secim_Ismi'].isin(secilen_yeni_urunler)].copy()
                yeni_df['Adet'] = 1
                yeni_df = yeni_df[['Urun_Kodu', 'Urun_Adi', 'Fiyat', 'Adet', 'Secim_Ismi']]
                yeni_df.rename(columns={'Fiyat': 'Liste_Fiyati'}, inplace=True)
                
                # Mevcut sepete ekle (concat)
                st.session_state['sepet'] = pd.concat([st.session_state['sepet'], yeni_df], ignore_index=True)
                # Aynı ürün varsa alt alta ekler, kullanıcı birleştirmek isterse manuel yapar veya kod geliştirilebilir.
                st.success(f"{len(secilen_yeni_urunler)} ürün eklendi!")
                st.rerun() # Sayfayı yenile ki tablo güncellensin

    # --- 3. Sepet (Düzenleme ve Silme) ---
    st.write("---")
    st.subheader("2. Teklif Listesi (Düzenle / Sil)")
    
    if not st.session_state['sepet'].empty:
        st.info("💡 İpucu: Listeden ürün silmek için satırı seçip 'Delete' tuşuna basın veya tablonun sağındaki çöp kutusuna tıklayın.")
        
        # Data Editor: Buradaki değişiklikler anında kaydedilir
        # num_rows="dynamic" özelliği satır ekleme/silme imkanı verir
        duzenlenmis_sepet = st.data_editor(
            st.session_state['sepet'],
            column_config={
                "Adet": st.column_config.NumberColumn("Adet", min_value=1, step=1),
                "Liste_Fiyati": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f €", disabled=True),
                "Secim_Ismi": None, # Bu sütunu tabloda gizle, kalabalık etmesin
            },
            hide_index=True,
            num_rows="dynamic", # SİLME ÖZELLİĞİNİ BU AÇIYOR
            key="sepet_editor" # Benzersiz ID
        )
        
        # Sepeti güncelle (Eğer kullanıcı sildiyse veya adet değiştirdiyse)
        # Sadece boş olmayan satırları tut (Kullanıcı boş satır eklerse diye önlem)
        duzenlenmis_sepet = duzenlenmis_sepet[duzenlenmis_sepet['Urun_Kodu'].notna()]
        st.session_state['sepet'] = duzenlenmis_sepet

        # --- 4. Hesaplama ve Çıktı ---
        st.write("---")
        
        col1, col2 = st.columns(2)
        with col1:
            hesap_tipi = st.radio("İşlem:", ["İskonto (%)", "Kâr Ekle (%)"], horizontal=True)
        with col2:
            oran = st.number_input("Yüzde:", min_value=0.0, value=0.0, step=1.0)

        # Hesaplamalar
        teklif_df = st.session_state['sepet'].copy()
        
        if hesap_tipi == "İskonto (%)":
            teklif_df['Birim_Son_Fiyat'] = teklif_df['Liste_Fiyati'] * (1 - oran/100)
        else:
            teklif_df['Birim_Son_Fiyat'] = teklif_df['Liste_Fiyati'] * (1 + oran/100)

        teklif_df['Toplam_Tutar'] = teklif_df['Birim_Son_Fiyat'] * teklif_df['Adet']
        genel_toplam = teklif_df['Toplam_Tutar'].sum()

        st.metric(label="TOPLAM (Euro)", value=f"€ {genel_toplam:,.2f}")

        # İndirme Butonu
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Çıktıda gereksiz sütunları atalım
            cikti_df = teklif_df[['Urun_Kodu', 'Urun_Adi', 'Adet', 'Liste_Fiyati', 'Birim_Son_Fiyat', 'Toplam_Tutar']]
            cikti_df.to_excel(writer, index=False, sheet_name='Teklif')
            
            workbook = writer.book
            worksheet = writer.sheets['Teklif']
            para_format = workbook.add_format({'num_format': '€ #,##0.00'})
            
            worksheet.set_column('D:F', 15, para_format)
            worksheet.set_column('B:B', 30)

        output.seek(0)
        tarih = datetime.datetime.now().strftime("%Y-%m-%d")
        st.download_button(
            "📥 Teklifi İndir (Excel)",
            data=output,
            file_name=f"Teklif_{tarih}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # Sepeti Temizle Butonu
        if st.button("🗑️ Tüm Listeyi Temizle"):
            st.session_state['sepet'] = pd.DataFrame(columns=['Urun_Kodu', 'Urun_Adi', 'Liste_Fiyati', 'Adet', 'Secim_Ismi'])
            st.rerun()

    else:
        st.info("Sepetiniz boş. Yukarıdan ürün arayıp ekleyebilirsiniz.")
