from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
# Default Qari
DEFAULT_QARI_PER_AYAT = "ar.alafasy"
DEFAULT_QARI_FULL = "Abdullah-Al-Juhany"

app = Flask(__name__)
CORS(app)


# ===============================
# KONEKSI DATABASE
# ===============================
def get_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="db_alqur`an"  # Perbaikan: hapus backtick
        )
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


def get_cursor(dict_mode=False):
    """
    Helper untuk mengambil koneksi + cursor
    dict_mode=True -> hasil fetch dalam bentuk dictionary
    """
    db = get_db()
    if db is None:
        return None, None
    if dict_mode:
        return db, db.cursor(dictionary=True)
    return db, db.cursor()


# ===============================
# 1. GET Semua Surat
# ===============================
@app.route("/api/surah", methods=["GET"])
def get_all_surah():
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("SELECT * FROM surah ORDER BY id ASC")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "total": len(data), "surah": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 2. GET Detail Surat + Ayat
# ===============================
@app.route("/api/surah/<int:surah_id>", methods=["GET"])
def get_surah_detail(surah_id):
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500

        cursor.execute("SELECT * FROM surah WHERE id = %s", (surah_id,))
        surah = cursor.fetchone()

        if not surah:
            cursor.close()
            db.close()
            return jsonify({"status": "error", "message": "Surah tidak ditemukan"}), 404

        cursor.execute("""
            SELECT nomor_ayat, teks_arab, teks_latin, teks_indonesia
            FROM ayat
            WHERE surah_id = %s
            ORDER BY nomor_ayat ASC
        """, (surah_id,))
        ayat = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify({
            "status": "success",
            "surah": surah,
            "ayat": ayat
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 3. GET Semua Ayat
# ===============================
@app.route("/api/ayat", methods=["GET"])
def get_all_ayat():
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("SELECT * FROM ayat ORDER BY surah_id, nomor_ayat ASC")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "total": len(data), "ayat": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 4. SEARCH Ayat (Arab + Terjemahan)
# ===============================
@app.route("/api/search", methods=["GET"])
def search_ayat():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "Query parameter 'q' dibutuhkan"}), 400

        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("""
            SELECT a.surah_id, s.nama AS nama_surah, a.nomor_ayat,
                   a.teks_arab, a.teks_latin, a.teks_indonesia
            FROM ayat a
            JOIN surah s ON a.surah_id = s.id
            WHERE a.teks_arab LIKE %s
               OR a.teks_indonesia LIKE %s
            ORDER BY a.surah_id, a.nomor_ayat
        """, (f"%{query}%", f"%{query}%"))

        data = cursor.fetchall()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "total": len(data), "results": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 5. SEARCH Terjemahan Indonesia saja
# ===============================
@app.route("/api/search/terjemahan", methods=["GET"])
def search_terjemahan():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "Query parameter 'q' dibutuhkan"}), 400

        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("""
            SELECT a.surah_id, s.nama AS nama_surah, a.nomor_ayat,
                   a.teks_arab, a.teks_latin, a.teks_indonesia
            FROM ayat a
            JOIN surah s ON a.surah_id = s.id
            WHERE a.teks_indonesia LIKE %s
            ORDER BY a.surah_id, a.nomor_ayat
        """, (f"%{query}%",))

        data = cursor.fetchall()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "total": len(data), "results": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 6. AUDIO PER AYAT
# ===============================
@app.route("/api/audio/<int:surah>/<int:ayat>", methods=["GET"])
def audio_ayat(surah, ayat):
    try:
        surah_str = str(surah).zfill(3)
        ayat_str = str(ayat).zfill(3)

        audio_url = f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayat_str}.mp3"

        return jsonify({
            "status": "success",
            "surah": surah,
            "ayat": ayat,
            "audio_url": audio_url
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 7. AUDIO FULL SURAH
# ===============================
@app.route("/api/audio/full/<int:surah>", methods=["GET"])
def audio_full(surah):
    try:
        surah_str = str(surah).zfill(3)

        audio_url = f"https://cdn.equran.id/audio-full/{DEFAULT_QARI_FULL}/{surah_str}.mp3"
        return jsonify({
            "status": "success",
            "surah": surah,
            "audio_url": audio_url
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 8. POST Bookmark
# ===============================
@app.route("/api/bookmark", methods=["POST"])
def add_bookmark():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Data JSON tidak valid"}), 400
        
        surah = data.get("surah")
        ayat = data.get("ayat")

        if not surah or not ayat:
            return jsonify({"status": "error", "message": "Surah dan Ayat harus diisi"}), 400

        db, cursor = get_cursor()
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("""
            INSERT INTO bookmark (surah, ayat)
            VALUES (%s, %s)
        """, (surah, ayat))
        db.commit()

        cursor.close()
        db.close()

        return jsonify({"status": "success", "message": "Bookmark ditambahkan"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 9. GET Bookmark
# ===============================
@app.route("/api/bookmark", methods=["GET"])
def get_bookmark():
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("SELECT * FROM bookmark ORDER BY id DESC")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "results": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 10. DELETE Bookmark
# ===============================
@app.route("/api/bookmark/<int:id>", methods=["DELETE"])
def delete_bookmark(id):
    try:
        db, cursor = get_cursor()
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("DELETE FROM bookmark WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "message": "Bookmark dihapus"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 11. POST Last Read
# ===============================
@app.route("/api/last_read", methods=["POST"])
def add_last_read():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Data JSON tidak valid"}), 400
        
        surah = data.get("surah")
        ayat = data.get("ayat")

        if not surah or not ayat:
            return jsonify({"status": "error", "message": "Surah dan Ayat harus diisi"}), 400

        db, cursor = get_cursor()
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500

        cursor.execute("DELETE FROM last_read")
        cursor.execute("""
            INSERT INTO last_read (surah, ayat)
            VALUES (%s, %s)
        """, (surah, ayat))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "message": "Last read diperbarui"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 12. GET Last Read
# ===============================
@app.route("/api/last_read", methods=["GET"])
def get_last_read():
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("SELECT * FROM last_read ORDER BY id DESC LIMIT 1")
        data = cursor.fetchone()
        cursor.close()
        db.close()

        if not data:
            return jsonify({"status": "success", "message": "Belum ada last read", "last_read": None})

        return jsonify({"status": "success", "last_read": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 13. GET Tafsir
# ===============================
@app.route("/api/tafsir/<int:surah_id>/<int:ayat>", methods=["GET"])
def get_tafsir(surah_id, ayat):
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("""
            SELECT * FROM tafsir
            WHERE surah_id = %s AND ayat = %s
            LIMIT 1
        """, (surah_id, ayat))
        data = cursor.fetchone()
        cursor.close()
        db.close()

        if not data:
            return jsonify({"status": "error", "message": "Tafsir tidak ditemukan"}), 404

        return jsonify({"status": "success", "tafsir": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 14. POST Tambah Tafsir
# ===============================
@app.route("/api/tafsir", methods=["POST"])
def add_tafsir():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Data JSON tidak valid"}), 400
        
        surah_id = data.get("surah_id")
        ayat = data.get("ayat")
        tafsir_text = data.get("tafsir_text")

        if not surah_id or not ayat or not tafsir_text:
            return jsonify({"status": "error", "message": "Surah, Ayat, dan Tafsir wajib diisi"}), 400

        db, cursor = get_cursor()
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("""
            INSERT INTO tafsir (surah_id, ayat, tafsir_text)
            VALUES (%s, %s, %s)
        """, (surah_id, ayat, tafsir_text))
        db.commit()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "message": "Tafsir berhasil ditambahkan"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 15. GET Semua Juz
# ===============================
@app.route("/api/juz", methods=["GET"])
def get_all_juz():
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500
        
        cursor.execute("SELECT * FROM juz ORDER BY id ASC")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "total": len(data), "juz": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 16. GET Detail Juz
# ===============================
@app.route("/api/juz/<int:juz_id>", methods=["GET"])
def get_juz(juz_id):
    try:
        db, cursor = get_cursor(True)
        if db is None or cursor is None:
            return jsonify({"status": "error", "message": "Koneksi database gagal"}), 500

        # Ambil data Juz
        cursor.execute("SELECT * FROM juz WHERE id = %s", (juz_id,))
        juz = cursor.fetchone()
        if not juz:
            cursor.close()
            db.close()
            return jsonify({"status": "error", "message": "Juz tidak ditemukan"}), 404

        # Ambil ayat berdasarkan start_verse dan end_verse
        cursor.execute("""
            SELECT a.id AS ayat_id, a.surah_id, s.nama AS nama_surah, a.nomor_ayat,
                   a.teks_arab, a.teks_latin, a.teks_indonesia
            FROM ayat a
            JOIN surah s ON a.surah_id = s.id
            WHERE a.id BETWEEN %s AND %s
            ORDER BY a.id
        """, (juz['start_verse'], juz['end_verse']))
        ayat = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify({
            "status": "success",
            "juz": juz,
            "ayat": ayat
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)