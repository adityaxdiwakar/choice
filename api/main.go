package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"

	"github.com/adityaxdiwakar/flux"
	"github.com/adityaxdiwakar/tda-go"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
)

var up bool
var messages []string
var messageSync sync.Mutex

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
	s, err := flux.New(tdaSession, false, false)
	if err != nil {
		log.Fatal(err)
	}

	branch := make(chan string, 100)
	s.AddBranch(branch)
	s.Open()
	up = true

	go func() {
		for {
			b := <-branch
			messageSync.Lock()
			messages = append(messages, b)
			fmt.Println(len(messages))
			messageSync.Unlock()
		}
	}()

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

	r.Get("/quote/{underlying}/{min}/{max}", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Series-Name") == "" {
			encode("Please supply a series name in the header", w, 400)
			return
		}

		min, errA := strconv.ParseFloat(chi.URLParam(r, "min"), 64)
		max, errB := strconv.ParseFloat(chi.URLParam(r, "max"), 64)
		if errA != nil || errB != nil {
			encode("Please enter only floats for the min/max params", w, 400)
			return
		}

		sig := flux.OptionQuoteRequestSignature{
			Underlying: chi.URLParam(r, "underlying"),
			Exchange:   "BEST",
			Fields: []flux.QuoteField{
				flux.Bid, flux.Ask, flux.ProbabilityITM, flux.Volume, flux.OpenInterest,
				flux.Last, flux.Mark, flux.MarkChange,
				flux.Delta, flux.Gamma, flux.Rho, flux.Theta, flux.Vega, flux.ImplVol,
			},
			Filter: flux.OptionQuoteFilter{
				SeriesNames: strings.Split(r.Header.Get("Series-Name"), ","),
				MinStrike:   min,
				MaxStrike:   max,
			},
		}

		s.RequestOptionQuote(sig, true)

		encode("OK.", w, 200)
	})

	r.Get("/quotes", func(w http.ResponseWriter, r *http.Request) {
		messageSync.Lock()
		defer messageSync.Unlock()
		encode(messages, w, 200)
		messages = []string{}
	})

	r.Get("/status", func(w http.ResponseWriter, r *http.Request) {
		encode(up && s.Established, w, 200)
		return
	})

	r.Post("/restart", func(w http.ResponseWriter, r *http.Request) {
		s.Restart()
		encode(up && s.Established, w, 200)
		return
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
