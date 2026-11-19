"use client";

import { type FormEvent, useState } from "react";

type Props = {
  initial: string;
  placeholder?: string;
  onSearch: (keyword: string) => void;
};

/** キーワード1つの検索フォーム。URL の条件が変わったときは key を変えて作り直す。 */
export function KeywordSearchForm({ initial, placeholder, onSearch }: Props) {
  const [keyword, setKeyword] = useState(initial);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSearch(keyword);
  };

  return (
    <form className="search-form card" onSubmit={submit} role="search">
      <label className="field">
        キーワード
        <input
          type="search"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder={placeholder}
        />
      </label>
      <div>
        <button type="submit">検索</button>
      </div>
    </form>
  );
}
