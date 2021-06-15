package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/adityaxdiwakar/flux"
	"github.com/adityaxdiwakar/tda-go"
	"github.com/go-chi/chi/middleware"
	"github.com/go-chi/chi/v5"
)

type PayloadResponse struct {
	Payload interface{} `json:"payload"`
	Code    int         `json:"status_code"`
}

func main() {
	// initialize the tda session
	tdaSession := tda.Session{
		Refresh:     REFRESH_TOKEN,
		ConsumerKey: CONSUMER_KEY,
		RootUrl:     "https://api.tdameritrade.com/v1",
	}

	// initialize the flux session
	s, err := flux.New(tdaSession, true)
	if err != nil {
		log.Fatal(err)
	}
	s.Open()

	// init the chi router
	r := chi.NewRouter()
	r.Use(middleware.Logger)

	r.Get("/series/{ticker}", func(w http.ResponseWriter, r *http.Request) {
		sig := flux.OptionSeriesRequestSignature{
			Ticker: chi.URLParam(r, "ticker"),
		}

		payload, err := s.RequestOptionSeries(sig)

		if err != nil {
			encode(fmt.Sprintf("%v", err), w, 500)
			return
		}

		encode(payload, w, 200)
	})

	r.Get("/chain/{underlying}", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Series-Name") == "" {
			encode("Please supply a series name in the header", w, 400)
			return
		}

		sig := flux.OptionChainGetRequestSignature{
			Underlying: chi.URLParam(r, "underlying"),
			Filter: flux.OptionChainGetFilter{
				StrikeQuantity: 1<<31 - 1,
				SeriesNames:    []string{r.Header.Get("Series-Name")},
			},
		}

		payload, err := s.RequestOptionChainGet(sig)

		if err != nil {
			encode(fmt.Sprintf("%v", err), w, 500)
			return
		}

		encode(payload, w, 200)
	})

	r.Get("/chart/{ticker}/{range}/{width}", func(w http.ResponseWriter, r *http.Request) {
		sig := flux.ChartRequestSignature{
			Ticker: chi.URLParam(r, "ticker"),
			Range:  chi.URLParam(r, "range"),
			Width:  chi.URLParam(r, "width"),
		}

		payload, err := s.RequestChart(sig)

		if err != nil {
			encode(fmt.Sprintf("%v", err), w, 500)
			return
		}

		encode(payload, w, 200)
	})

	http.ListenAndServe(":7731", r)

}

func encode(data interface{}, w http.ResponseWriter, statusCode int) {
	w.WriteHeader(statusCode)
	w.Header().Set("Content-Type", "application/json")
	resp := PayloadResponse{
		Payload: data,
		Code:    statusCode,
	}
	str, _ := json.MarshalIndent(resp, "", "    ")
	str = bytes.Replace(str, []byte("\\u003c"), []byte("<"), -1)
	str = bytes.Replace(str, []byte("\\u003e"), []byte(">"), -1)
	str = bytes.Replace(str, []byte("\\u0026"), []byte("&"), -1)
	w.Write(str)
}
