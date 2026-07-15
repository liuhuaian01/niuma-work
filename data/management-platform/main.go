// ============================================================
// Super Niuma 管理平台 — Phase 0: 激活码 + 版本管理
// Go + Gin + PostgreSQL
// ============================================================

package main

import (
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"golang.org/x/crypto/bcrypt"
)

// ── Config ──
var (
	db          *sql.DB
	jwtSecret   = []byte(getEnv("JWT_SECRET", "super-niuma-dev-secret-change-in-production"))
	listenAddr  = getEnv("LISTEN_ADDR", ":8080")
	dbURL       = getEnv("DATABASE_URL", "postgres://niuma:niuma@localhost:5432/niuma?sslmode=disable")
)

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// ── Models ──

type Admin struct {
	ID           string    `json:"id"`
	Email        string    `json:"email"`
	Role         string    `json:"role"`
	LastLoginAt  *time.Time `json:"last_login_at"`
}

type InviteBatch struct {
	ID        string    `json:"id"`
	BatchName string    `json:"batch_name"`
	CodeType  string    `json:"code_type"`
	Count     int       `json:"count"`
	Channel   string    `json:"channel"`
	CreatedAt time.Time `json:"created_at"`
}

type InviteCode struct {
	ID             string     `json:"id"`
	Code           string     `json:"code"`
	Type           string     `json:"type"`
	BatchID        *string    `json:"batch_id"`
	Status         string     `json:"status"`
	UsedBy         *string    `json:"used_by"`
	UsedAt         *time.Time `json:"used_at"`
	ExpiresAt      *time.Time `json:"expires_at"`
	PlanDurationDays int      `json:"plan_duration_days"`
	MaxUses        int        `json:"max_uses"`
	CurrentUses    int        `json:"current_uses"`
}

type AppVersion struct {
	ID             string    `json:"id"`
	Version        string    `json:"version"`
	Platform       string    `json:"platform"`
	DownloadURL    string    `json:"download_url"`
	Changelog      string    `json:"changelog"`
	SizeMB         float64   `json:"size_mb"`
	Required       bool      `json:"required"`
	RolloutPercent int       `json:"rollout_percent"`
	Status         string    `json:"status"`
}

type User struct {
	ID          string `json:"id"`
	Email       string `json:"email"`
	Nickname    string `json:"nickname"`
	Plan        string `json:"plan"`
	InviteCode  string `json:"invite_code"`
}

type Device struct {
	ID           string    `json:"id"`
	UserID       string    `json:"user_id"`
	DeviceIDHash string    `json:"device_id_hash"`
	DeviceName   string    `json:"device_name"`
	Platform     string    `json:"platform"`
	AppVersion   string    `json:"app_version"`
	LastPingAt   time.Time `json:"last_ping_at"`
}

// ── JWT ──

type Claims struct {
	AdminID string `json:"admin_id"`
	Email   string `json:"email"`
	Role    string `json:"role"`
	jwt.RegisteredClaims
}

func generateJWT(admin Admin) (string, error) {
	claims := Claims{
		AdminID: admin.ID,
		Email:   admin.Email,
		Role:    admin.Role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(jwtSecret)
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		auth := c.GetHeader("Authorization")
		if !strings.HasPrefix(auth, "Bearer ") {
			c.JSON(401, gin.H{"success": false, "error": gin.H{"code": "unauthorized", "message": "缺少认证令牌"}})
			c.Abort()
			return
		}
		tokenStr := strings.TrimPrefix(auth, "Bearer ")
		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
			return jwtSecret, nil
		})
		if err != nil || !token.Valid {
			c.JSON(401, gin.H{"success": false, "error": gin.H{"code": "unauthorized", "message": "令牌无效或已过期"}})
			c.Abort()
			return
		}
		c.Set("admin_id", claims.AdminID)
		c.Set("admin_email", claims.Email)
		c.Next()
	}
}

// ── Activation Code Generator ──

const codeChars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789" // removed 0/O/1/I/L

func generateCode() string {
	segments := make([]string, 3)
	for i := 0; i < 3; i++ {
		b := make([]byte, 4)
		for j := 0; j < 4; j++ {
			n, _ := rand.Int(rand.Reader, big.NewInt(int64(len(codeChars))))
			b[j] = codeChars[n.Int64()]
		}
		segments[i] = string(b)
	}
	return "NIUA-" + segments[0] + "-" + segments[1] + "-" + segments[2]
}

// ── Handlers ──

// POST /v1/auth/login
func handleLogin(c *gin.Context) {
	var req struct {
		Email    string `json:"email" binding:"required"`
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_params", "message": err.Error()}})
		return
	}

	var admin Admin
	var hash string
	err := db.QueryRow("SELECT id, email, password_hash, role FROM admins WHERE email = $1", req.Email).
		Scan(&admin.ID, &admin.Email, &hash, &admin.Role)
	if err == sql.ErrNoRows {
		c.JSON(401, gin.H{"success": false, "error": gin.H{"code": "invalid_credentials", "message": "邮箱或密码错误"}})
		return
	}
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error", "message": "数据库错误"}})
		return
	}

	if bcrypt.CompareHashAndPassword([]byte(hash), []byte(req.Password)) != nil {
		c.JSON(401, gin.H{"success": false, "error": gin.H{"code": "invalid_credentials", "message": "邮箱或密码错误"}})
		return
	}

	token, err := generateJWT(admin)
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "token_error", "message": "令牌生成失败"}})
		return
	}

	db.Exec("UPDATE admins SET last_login_at = NOW() WHERE id = $1", admin.ID)

	c.JSON(200, gin.H{
		"success": true,
		"data":    gin.H{"token": token, "admin": admin},
	})
}

// POST /v1/admin/codes/generate
func handleGenerateCodes(c *gin.Context) {
	var req struct {
		BatchName        string `json:"batch_name" binding:"required"`
		CodeType         string `json:"code_type" binding:"required"`
		Count            int    `json:"count" binding:"required,min=1,max=1000"`
		Channel          string `json:"channel"`
		PlanDurationDays int    `json:"plan_duration_days"`
		ExpiresAt        string `json:"expires_at"` // ISO 8601, optional
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_params", "message": err.Error()}})
		return
	}
	if req.PlanDurationDays <= 0 {
		req.PlanDurationDays = 30
	}

	adminID := c.GetString("admin_id")

	// Create batch
	var batchID string
	err := db.QueryRow(
		"INSERT INTO invite_batches (batch_name, code_type, count, channel, created_by) VALUES ($1,$2,$3,$4,$5) RETURNING id",
		req.BatchName, req.CodeType, req.Count, req.Channel, adminID,
	).Scan(&batchID)
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error", "message": "创建批次失败"}})
		return
	}

	// Generate codes
	codes := make([]InviteCode, req.Count)
	for i := 0; i < req.Count; i++ {
		code := generateCode()
		var expiresAt *time.Time
		if req.ExpiresAt != "" {
			t, _ := time.Parse(time.RFC3339, req.ExpiresAt)
			expiresAt = &t
		}
		var id string
		err := db.QueryRow(
			`INSERT INTO invite_codes (code, type, batch_id, expires_at, plan_duration_days, created_by) 
			 VALUES ($1,$2,$3,$4,$5,$6) RETURNING id`,
			code, req.CodeType, batchID, expiresAt, req.PlanDurationDays, adminID,
		).Scan(&id)
		if err != nil {
			c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error", "message": fmt.Sprintf("生成第 %d 个激活码失败", i+1)}})
			return
		}
		codes[i] = InviteCode{ID: id, Code: code, Type: req.CodeType, BatchID: &batchID, Status: "unused", PlanDurationDays: req.PlanDurationDays}
	}

	c.JSON(201, gin.H{
		"success": true,
		"data":    gin.H{"batch_id": batchID, "count": req.Count, "codes": codes},
	})
}

// GET /v1/admin/codes
func handleListCodes(c *gin.Context) {
	status := c.DefaultQuery("status", "")
	batchID := c.DefaultQuery("batch_id", "")
	page := c.DefaultQuery("page", "1")

	query := "SELECT id, code, type, batch_id, status, plan_duration_days, current_uses, max_uses, created_at FROM invite_codes WHERE 1=1"
	args := []interface{}{}
	argIdx := 1

	if status != "" {
		query += fmt.Sprintf(" AND status = $%d", argIdx)
		args = append(args, status)
		argIdx++
	}
	if batchID != "" {
		query += fmt.Sprintf(" AND batch_id = $%d", argIdx)
		args = append(args, batchID)
		argIdx++
	}
	query += fmt.Sprintf(" ORDER BY created_at DESC LIMIT 50 OFFSET $%d", argIdx)
	// Simple offset calculation
	pageNum := 1
	fmt.Sscanf(page, "%d", &pageNum)
	args = append(args, (pageNum-1)*50)

	rows, err := db.Query(query, args...)
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error", "message": "查询失败"}})
		return
	}
	defer rows.Close()

	codes := []InviteCode{}
	for rows.Next() {
		var ic InviteCode
		rows.Scan(&ic.ID, &ic.Code, &ic.Type, &ic.BatchID, &ic.Status, &ic.PlanDurationDays, &ic.CurrentUses, &ic.MaxUses, &ic.CreatedAt)
		codes = append(codes, ic)
	}

	c.JSON(200, gin.H{"success": true, "data": gin.H{"codes": codes, "count": len(codes)}})
}

// POST /v1/codes/validate (public — called by client)
func handleValidateCode(c *gin.Context) {
	var req struct {
		Code string `json:"code" binding:"required,len=19"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_code", "message": "激活码格式不正确"}})
		return
	}

	var ic InviteCode
	err := db.QueryRow(
		"SELECT id, code, type, status, plan_duration_days, max_uses, current_uses, expires_at FROM invite_codes WHERE code = $1",
		req.Code,
	).Scan(&ic.ID, &ic.Code, &ic.Type, &ic.Status, &ic.PlanDurationDays, &ic.MaxUses, &ic.CurrentUses, &ic.ExpiresAt)

	if err == sql.ErrNoRows {
		c.JSON(404, gin.H{"success": false, "error": gin.H{"code": "invalid_code", "message": "激活码不存在"}})
		return
	}
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error"}})
		return
	}

	if ic.Status == "revoked" {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "code_revoked", "message": "激活码已被禁用"}})
		return
	}
	if ic.Status == "used" && ic.CurrentUses >= ic.MaxUses {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "code_used", "message": "激活码已被使用"}})
		return
	}
	if ic.ExpiresAt != nil && time.Now().After(*ic.ExpiresAt) {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "code_expired", "message": "激活码已过期"}})
		return
	}

	c.JSON(200, gin.H{
		"success": true,
		"data": gin.H{
			"code":              ic.Code,
			"type":              ic.Type,
			"plan_duration_days": ic.PlanDurationDays,
			"valid":             true,
		},
	})
}

// POST /v1/version/check (public — called by client)
func handleVersionCheck(c *gin.Context) {
	var req struct {
		Current  string `json:"current" binding:"required"`
		Platform string `json:"platform"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_params"}})
		return
	}
	if req.Platform == "" {
		req.Platform = "win32"
	}

	var av AppVersion
	err := db.QueryRow(
		`SELECT version, download_url, changelog, size_mb, required, rollout_percent 
		 FROM app_versions 
		 WHERE platform = $1 AND status = 'published' 
		 ORDER BY published_at DESC LIMIT 1`,
		req.Platform,
	).Scan(&av.Version, &av.DownloadURL, &av.Changelog, &av.SizeMB, &av.Required, &av.RolloutPercent)

	if err == sql.ErrNoRows {
		c.JSON(200, gin.H{"success": true, "data": gin.H{"latest": req.Current, "update_available": false}})
		return
	}
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error"}})
		return
	}

	updateAvailable := av.Version != req.Current

	c.JSON(200, gin.H{
		"success": true,
		"data": gin.H{
			"latest":           av.Version,
			"update_available": updateAvailable,
			"download_url":     av.DownloadURL,
			"changelog":        av.Changelog,
			"size_mb":          av.SizeMB,
			"required":         av.Required,
		},
	})
}

// POST /v1/admin/versions
func handlePublishVersion(c *gin.Context) {
	var req struct {
		Version        string  `json:"version" binding:"required"`
		Platform       string  `json:"platform"`
		DownloadURL    string  `json:"download_url" binding:"required"`
		Changelog      string  `json:"changelog"`
		SizeMB         float64 `json:"size_mb"`
		Required       bool    `json:"required"`
		RolloutPercent int     `json:"rollout_percent"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_params", "message": err.Error()}})
		return
	}
	if req.Platform == "" {
		req.Platform = "win32"
	}
	if req.RolloutPercent == 0 {
		req.RolloutPercent = 100
	}

	_, err := db.Exec(
		`INSERT INTO app_versions (version, platform, download_url, changelog, size_mb, required, rollout_percent, status, published_at) 
		 VALUES ($1,$2,$3,$4,$5,$6,$7,'published',NOW())`,
		req.Version, req.Platform, req.DownloadURL, req.Changelog, req.SizeMB, req.Required, req.RolloutPercent,
	)
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error", "message": "发布版本失败"}})
		return
	}

	c.JSON(201, gin.H{"success": true, "data": gin.H{"version": req.Version, "platform": req.Platform}})
}

// POST /v1/devices/ping (public — called by client)
func handlePing(c *gin.Context) {
	var req struct {
		DeviceID    string `json:"device_id"`
		DeviceName  string `json:"device_name"`
		Platform    string `json:"platform"`
		AppVersion  string `json:"version"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"success": false, "error": gin.H{"code": "invalid_params"}})
		return
	}

	hash := sha256.Sum256([]byte(req.DeviceID))
	hashStr := hex.EncodeToString(hash[:])

	// Upsert device
	_, err := db.Exec(
		`INSERT INTO devices (device_id_hash, device_name, platform, app_version, last_ping_at) 
		 VALUES ($1,$2,$3,$4,NOW())
		 ON CONFLICT (device_id_hash) DO UPDATE SET last_ping_at = NOW(), app_version = $4`,
		hashStr, req.DeviceName, req.Platform, req.AppVersion,
	)
	if err != nil {
		c.JSON(500, gin.H{"success": false, "error": gin.H{"code": "db_error"}})
		return
	}

	// Accumulate daily stat
	db.Exec(
		`INSERT INTO daily_stats (date, dau, ping_count) VALUES (CURRENT_DATE, 1, 1)
		 ON CONFLICT (date) DO UPDATE SET dau = daily_stats.dau + 1, ping_count = daily_stats.ping_count + 1`,
	)

	// Check for messages/notices (Phase 3 feature, placeholder)
	c.JSON(200, gin.H{
		"success": true,
		"data": gin.H{
			"server_time": time.Now().UTC().Format(time.RFC3339),
			"messages":    []interface{}{},
		},
	})
}

// GET /v1/admin/dashboard
func handleDashboard(c *gin.Context) {
	var dau, newActivations, totalUsers, totalCodes int
	var unusedCodes int

	db.QueryRow("SELECT COALESCE(dau, 0) FROM daily_stats WHERE date = CURRENT_DATE").Scan(&dau)
	db.QueryRow("SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE").Scan(&newActivations)
	db.QueryRow("SELECT COUNT(*) FROM users").Scan(&totalUsers)
	db.QueryRow("SELECT COUNT(*) FROM invite_codes").Scan(&totalCodes)
	db.QueryRow("SELECT COUNT(*) FROM invite_codes WHERE status = 'unused'").Scan(&unusedCodes)

	c.JSON(200, gin.H{
		"success": true,
		"data": gin.H{
			"dau":              dau,
			"new_activations":  newActivations,
			"total_users":      totalUsers,
			"total_codes":      totalCodes,
			"unused_codes":     unusedCodes,
		},
	})
}

// ── Main ──

func main() {
	var err error
	db, err = sql.Open("postgres", dbURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	if err = db.Ping(); err != nil {
		log.Fatalf("Database ping failed: %v", err)
	}
	log.Println("Database connected")

	// Run migrations
	schema, _ := os.ReadFile("schema.sql")
	_, err = db.Exec(string(schema))
	if err != nil {
		log.Printf("Migration warning: %v", err)
	} else {
		log.Println("Migrations applied")
	}

	// Setup router
	r := gin.Default()
	r.SetTrustedProxies(nil)

	// CORS
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type,Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// ── Public routes ──
	v1 := r.Group("/v1")
	{
		v1.POST("/auth/login", handleLogin)
		v1.POST("/codes/validate", handleValidateCode)
		v1.POST("/version/check", handleVersionCheck)
		v1.POST("/devices/ping", handlePing)
	}

	// ── Admin routes (JWT required) ──
	admin := r.Group("/v1/admin")
	admin.Use(authMiddleware())
	{
		admin.GET("/dashboard", handleDashboard)
		admin.POST("/codes/generate", handleGenerateCodes)
		admin.GET("/codes", handleListCodes)
		admin.POST("/versions", handlePublishVersion)
	}

	// ── Health check ──
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	log.Printf("管理平台启动: %s", listenAddr)
	r.Run(listenAddr)
}
